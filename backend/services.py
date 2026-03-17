
import os
import logging
import asyncio
from typing import Dict, Any, Optional
import redis.asyncio as redis
from .config import settings
from .database import create_db_and_tables, engine as db_engine
from .security.vault import VaultManager
from .security.verus import SovereignIdentity
from .inference.router import ModelRouter
from .security.guardrail import GuardrailScanner
from .ace.engine import AffectiveEngine
from .skill_manager import SkillManager
from .memory.manager import MemoryManager
from .analytics import UsageTracker
from .orchestrator import ExecutiveOrchestrator
from .tasks import TaskManager
from .inference.local_bridge import LocalInferenceBridge
from .ws_gateway import JsonRpcGateway
from .exec_approval import ExecApprovalManager
from .cron_engine import CronEngine
from .config_editor import ConfigEditor
from .updater import updater as updater_instance
from .log_streamer import log_buffer
from .device_manager import DeviceManager
from .goals.engine import goal_engine as goal_engine_instance
from .sop.engine import sop_engine as sop_engine_instance
from .logging_config import get_logger

logger = get_logger("PolytopeServices")

# Global Service Instances
vault: Optional[VaultManager] = None
router: Optional[ModelRouter] = None
ace: Optional[AffectiveEngine] = None
orchestrator: Optional[ExecutiveOrchestrator] = None
task_manager: Optional[TaskManager] = None
skill_manager: Optional[SkillManager] = None
sovereign_identity: Optional[SovereignIdentity] = None
local_inference: Optional[LocalInferenceBridge] = None
ws_gw: Optional[JsonRpcGateway] = None
usage_tracker: Optional[UsageTracker] = None
cron_engine: Optional[CronEngine] = None
config_editor: Optional[ConfigEditor] = None
exec_approval: Optional[ExecApprovalManager] = None
memory: Optional[MemoryManager] = None
redis_client: Optional[redis.Redis] = None
scanner: Optional[GuardrailScanner] = None
device_manager: Optional[DeviceManager] = None
goal_engine = goal_engine_instance
sop_engine = sop_engine_instance
updater = updater_instance
channel_registry: Dict[str, Any] = {}

async def init_services(app_instance):
    global vault, router, ace, orchestrator, task_manager, skill_manager, sovereign_identity
    global local_inference, ws_gw, usage_tracker, cron_engine, config_editor, exec_approval
    global memory, redis_client, scanner, device_manager

    logger.info("[ SERVICES ] Initializing global system components...")

    # 1. Redis Cache
    from .metrics import metrics
    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
            from fastapi_limiter import FastAPILimiter
            await FastAPILimiter.init(redis_client)
            logger.info(f"[ CACHE ]: Redis distributed rate limiter online: {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"[ CACHE ]: Redis initialization failed — rate limiting DISABLED: {e}")
            metrics.increment_counter("redis_init_failures_total")
    else:
        logger.warning("[ CACHE ]: REDIS_URL not configured. Rate limiting is INACTIVE.")
        metrics.increment_counter("redis_not_configured_total")

    # 2. Database & Data Layout
    create_db_and_tables()
    vault_root = os.path.expanduser("~/.polytope/vaults")
    os.makedirs(vault_root, exist_ok=True)

    # 3. Security Layer
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    sovereign_identity = SovereignIdentity(settings)

    # 4. Inference Layer
    router = ModelRouter(settings)
    scanner = GuardrailScanner(router)

    # 5. Affective Engine
    ace = AffectiveEngine()

    # 6. Skill Manager
    skill_manager = SkillManager(vault)

    # 7. Persistent Memory
    memory = MemoryManager()

    # 8. Usage & Cost Analytics
    usage_tracker = UsageTracker(db_engine)

    # 9. Executive Orchestrator
    orchestrator = ExecutiveOrchestrator(
        router, vault, ace, settings, 
        skill_manager=skill_manager, 
        analytics=usage_tracker,
        memory_manager=memory
    )

    # 10. Task Manager
    task_manager = TaskManager()

    # 11. Local Inference Bridge
    local_inference = LocalInferenceBridge(settings)

    # 12. WebSocket Gateway
    ws_gw = JsonRpcGateway(jwt_secret=settings.JWT_SECRET_KEY)
    
    # 13. Approval System
    exec_approval = ExecApprovalManager(db_engine, ws_gateway=ws_gw)
    
    # Wire references
    orchestrator.approval_manager = exec_approval
    orchestrator.executor.approval_manager = exec_approval
    orchestrator.ws_gateway = ws_gw
    router.ws_gateway = ws_gw

    # Register MemoryAdapter with the live MemoryManager instance.
    # Must happen after orchestrator (and thus adapter_registry) is created.
    from .adapters.memory_adapter import MemoryAdapter
    orchestrator.adapter_registry.register(MemoryAdapter(memory))
    logger.info("[ ADAPTERS ] MemoryAdapter registered — memory_search/memory_store tools active.")

    # 14. Self-Update Manager
    await updater.start()

    # 15. Inject services into Gateway
    ws_gw.inject_services(vault=vault, router=router, orchestrator=orchestrator, 
                          channel_registry=channel_registry, db_engine=db_engine,
                          updater=updater)

    # 16. Cron Engine
    cron_engine = CronEngine(db_engine, orchestrator=orchestrator, task_manager=task_manager)
    await cron_engine.start()

    # 17. Log Streamer
    log_buffer.install_handler()

    # 18. Config Editor
    config_editor = ConfigEditor(settings)

    # 19. Device Manager
    device_manager = DeviceManager(vault_root)

    # 20. Channel Adapter Registry
    await _init_channels(vault_root)

    # Start background token refresh loops for OAuth bridges
    from .config import settings as cfg
    oauth_refresh_config = {
        "slack":       {"token_url": "https://slack.com/api/tooling.tokens.rotate",
                        "client_id": getattr(cfg,"SLACK_CLIENT_ID",""),
                        "client_secret": getattr(cfg,"SLACK_CLIENT_SECRET","")},
        "discord":     {"token_url": "https://discord.com/api/oauth2/token",
                        "client_id": getattr(cfg,"DISCORD_CLIENT_ID",""),
                        "client_secret": getattr(cfg,"DISCORD_CLIENT_SECRET","")},
        "google_chat": {"token_url": "https://oauth2.googleapis.com/token",
                        "client_id": getattr(cfg,"GOOGLE_CLIENT_ID",""),
                        "client_secret": getattr(cfg,"GOOGLE_CLIENT_SECRET","")},
        "msteams":     {"token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                        "client_id": getattr(cfg,"MSTEAMS_CLIENT_ID",""),
                        "client_secret": getattr(cfg,"MSTEAMS_CLIENT_SECRET","")},
    }
    for bridge_id, ocfg in oauth_refresh_config.items():
        adapter = channel_registry.get(bridge_id)
        if adapter and adapter.is_connected and ocfg["client_id"]:
            asyncio.create_task(
                adapter._token_refresh_loop(
                    get_creds_fn=lambda b=bridge_id: vault.retrieve_connection_secret(b,"default"),
                    set_creds_fn=lambda c,b=bridge_id: vault.store_connection_secret(b,"default",c),
                    token_url=ocfg["token_url"],
                    client_id=ocfg["client_id"],
                    client_secret=ocfg["client_secret"],
                ), name=f"refresh_{bridge_id}")
            logger.info(f"[ SERVICES ] Token refresh loop started for {bridge_id}")

    # 21. Background Services
    await orchestrator.start_background_services()

    logger.info("[ SERVICES ] All core systems actualized.")

async def _init_channels(vault_root: str):
    from .bridges.telegram import TelegramBridge
    from .bridges.whatsapp import WhatsAppBridge
    from .bridges.discord import DiscordBridge
    from .bridges.slack import SlackBridge
    from .bridges.email import EmailBridge
    from .bridges.signal import SignalBridge
    from .bridges.google_chat import GoogleChatBridge
    from .bridges.nostr import NostrBridge
    from .bridges.imessage import IMessageBridge
    from .bridges.instagram import InstagramBridge
    from .bridges.facebook import FacebookBridge
    from .bridges.x_twitter import XBridge
    from .bridges.msteams import MSTeamsBridge
    from .bridges.wechat import WeChatBridge
    from .bridges.iwatch import IWatchBridge
    from .bridges.icloud import ICloudBridge
    from .bridges.gmail import GmailBridge
    from .bridges.gdrive import GDriveBridge
    from .bridges.webchat import WebChatBridge

    async def broadcast_bridge_event(event: str, data: Any):
        if ws_gw:
            await ws_gw.broadcast_event(event, data)

    channel_registry["telegram"] = TelegramBridge("telegram", vault_root, vault_manager=vault)
    channel_registry["whatsapp"] = WhatsAppBridge("whatsapp", vault_root, vault_manager=vault)
    channel_registry["discord"] = DiscordBridge("discord", vault_root, vault_manager=vault)
    channel_registry["slack"] = SlackBridge("slack", vault_root, vault_manager=vault)
    channel_registry["email"] = EmailBridge("email", vault_root, vault_manager=vault)
    channel_registry["signal"] = SignalBridge("signal", vault_root, vault_manager=vault)
    channel_registry["google_chat"] = GoogleChatBridge("google_chat", vault_root, vault_manager=vault)
    channel_registry["nostr"] = NostrBridge("nostr", vault_root, vault_manager=vault)
    channel_registry["imessage"] = IMessageBridge("imessage", vault_root, vault_manager=vault)
    channel_registry["instagram"] = InstagramBridge("instagram", vault_root, vault_manager=vault)
    channel_registry["facebook"] = FacebookBridge("facebook", vault_root, vault_manager=vault)
    channel_registry["x"] = XBridge("x", vault_root, vault_manager=vault)
    channel_registry["msteams"] = MSTeamsBridge("msteams", vault_root, vault_manager=vault)
    channel_registry["wechat"] = WeChatBridge("wechat", vault_root, vault_manager=vault)
    channel_registry["iwatch"] = IWatchBridge("iwatch", vault_root, vault_manager=vault)
    channel_registry["icloud"] = ICloudBridge("icloud", vault_root, vault_manager=vault)
    channel_registry["gmail"] = GmailBridge("gmail", vault_root, vault_manager=vault)
    channel_registry["gdrive"] = GDriveBridge("gdrive", vault_root, vault_manager=vault)
    channel_registry["webchat"] = WebChatBridge("webchat", vault_root, vault_manager=vault)

    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "on_event"):
            adapter.on_event = broadcast_bridge_event
        if hasattr(adapter, "on_inbound"):
            adapter.on_inbound = orchestrator.handle_inbound_message

    # Auto-connect channels
    for ch_name, adapter in channel_registry.items():
        try:
            # 1. Check if enabled (default True)
            enabled_state = await vault.retrieve_secret(f"channel_{ch_name}_enabled")
            adapter.enabled = enabled_state.get("enabled", True) if enabled_state else True
            if not adapter.enabled: continue

            # 2. Multi-account discovery (P1-009 Standard)
            accounts = await vault.list_connections(ch_name)
            
            if accounts:
                for account_id in accounts:
                    creds = await vault.retrieve_connection_secret(ch_name, account_id)
                    if creds:
                        success = await adapter.connect(creds)
                        if success:
                            logger.info(f"[ CHANNELS ] Connected {ch_name} (Account: {account_id})")
            else:
                # 3. Legacy Fallback (Migration path)
                creds = await vault.retrieve_secret(f"channel_{ch_name}")
                if creds:
                    success = await adapter.connect(creds)
                    if success:
                        logger.info(f"[ CHANNELS ] Connected legacy {ch_name}")
                        # Auto-migrate if we have an account ID now
                        acc_id = creds.get("team_id") or creds.get("user_id") or "default"
                        await vault.store_connection_secret(ch_name, acc_id, creds)

        except Exception as e:
            logger.debug(f"[ CHANNELS ] {ch_name} connection error during boot: {e}")

async def shutdown_services():
    logger.info("[ SERVICES ] Shutting down...")
    if cron_engine: await cron_engine.stop()
    if orchestrator: await orchestrator.stop_background_services()
    if updater: await updater.stop()
    
    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "disconnect"):
            await adapter.disconnect()
