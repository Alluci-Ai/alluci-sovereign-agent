
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

logger = logging.getLogger("PolytopeServices")

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
updater = updater_instance
channel_registry: Dict[str, Any] = {}

async def init_services(app_instance):
    global vault, router, ace, orchestrator, task_manager, skill_manager, sovereign_identity
    global local_inference, ws_gw, usage_tracker, cron_engine, config_editor, exec_approval
    global memory, redis_client, scanner, device_manager

    logger.info("[ SERVICES ] Initializing global system components...")

    # 1. Redis Cache
    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
            from fastapi_limiter import FastAPILimiter
            await FastAPILimiter.init(redis_client)
            logger.info(f"[ CACHE ]: Redis initialized on {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"[ CACHE ]: Redis initialization failed: {e}")

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

    async def broadcast_bridge_event(event: str, data: Any):
        if ws_gw:
            await ws_gw.broadcast_event(event, data)

    channel_registry["telegram"] = TelegramBridge("telegram", vault_root)
    channel_registry["whatsapp"] = WhatsAppBridge("whatsapp", vault_root)
    channel_registry["discord"] = DiscordBridge("discord", vault_root)
    channel_registry["slack"] = SlackBridge("slack", vault_root)
    channel_registry["email"] = EmailBridge("email", vault_root)
    channel_registry["signal"] = SignalBridge("signal", vault_root)
    channel_registry["google_chat"] = GoogleChatBridge("google_chat", vault_root)
    channel_registry["nostr"] = NostrBridge("nostr", vault_root)
    channel_registry["imessage"] = IMessageBridge("imessage", vault_root)
    channel_registry["instagram"] = InstagramBridge("instagram", vault_root)
    channel_registry["facebook"] = FacebookBridge("facebook", vault_root)
    channel_registry["x"] = XBridge("x", vault_root)
    channel_registry["msteams"] = MSTeamsBridge("msteams", vault_root)

    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "on_event"):
            adapter.on_event = broadcast_bridge_event
        if hasattr(adapter, "on_inbound"):
            adapter.on_inbound = orchestrator.handle_inbound_message

    # Auto-connect channels
    for ch_name, adapter in channel_registry.items():
        try:
            enabled_state = await vault.retrieve_secret(f"channel_{ch_name}_enabled")
            adapter.enabled = enabled_state.get("enabled", True) if enabled_state else True
            if not adapter.enabled: continue

            creds = await vault.retrieve_secret(f"channel_{ch_name}")
            if creds:
                await adapter.connect(creds)
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
