
import os
import logging
import asyncio
from typing import Dict, Any, Optional
import redis.asyncio as redis
from backend.config import settings
from backend.database import create_db_and_tables, engine as db_engine
from backend.security.vault import VaultManager
from backend.security.verus import SovereignIdentity
from backend.inference.router import ModelRouter
from backend.security.guardrail import GuardrailScanner
from backend.ace.engine import AffectiveEngine
from backend.skill_manager import SkillManager
from backend.memory.manager import MemoryManager
from backend.memory.hlsm_manager import HLSMManager
from backend.analytics import UsageTracker
pass  # Orchestrator import deferred
from backend.tasks import TaskManager
from backend.inference.local_bridge import LocalInferenceBridge
from backend.ws_gateway import JsonRpcGateway
from backend.exec_approval import ExecApprovalManager
from backend.cron_engine import CronEngine
from backend.config_editor import ConfigEditor
from backend.updater import updater as updater_instance
from backend.log_streamer import log_buffer
from backend.device_manager import DeviceManager
from backend.goals.engine import goal_engine as goal_engine_instance
from backend.sop.engine import sop_engine as sop_engine_instance
from backend.pcl import ProactiveCognitionLoop
from backend.logging_config import get_logger

logger = get_logger("PolytopeServices")
try:
    from backend.orchestrator import ExecutiveOrchestrator
except Exception as e:
    ExecutiveOrchestrator = None  # type: ignore
    logger.warning(f"ExecutiveOrchestrator import failed: {e}")

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
memory: Optional[HLSMManager] = None
hlsm_manager: Optional[HLSMManager] = None
redis_client: Optional[redis.Redis] = None
scanner: Optional[GuardrailScanner] = None
device_manager: Optional[DeviceManager] = None
goal_engine = goal_engine_instance
sop_engine = sop_engine_instance
pcl: Optional[ProactiveCognitionLoop] = None
updater = updater_instance
channel_registry: Dict[str, Any] = {}

async def init_services(app_instance):
    global vault, router, ace, orchestrator, task_manager, skill_manager, sovereign_identity
    global local_inference, ws_gw, usage_tracker, cron_engine, config_editor, exec_approval
    global memory, hlsm_manager, redis_client, scanner, device_manager, pcl, goal_engine, sop_engine

    logger.info("[ SERVICES ] Initializing global system components...")

    # 1. Redis Cache
    from backend.metrics import metrics
    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
            from fastapi_limiter import FastAPILimiter
            await FastAPILimiter.init(redis_client)
            logger.info(f"[ CACHE ]: Redis distributed rate limiter online: {settings.REDIS_URL}")

            # Wire Redis into VerusID auth for persistent challenge storage
            from backend.security.verusid_auth import verus_auth as _verus_auth
            _verus_auth._redis = redis_client
            logger.info("[ VERUSID ] Redis-backed challenge store active.")
        except Exception as e:
            logger.error(f"[ CACHE ]: Redis initialization failed: {e}")
            redis_client = None
            metrics.increment_counter("redis_init_failures_total")
            if settings.APP_ENV == "production":
                logger.warning("WARNING: Redis initialization failed in production. Using fallback.")
    else:
        if settings.APP_ENV == "production":
            logger.warning("WARNING: REDIS_URL not configured for production environment. Using fallback.")
        logger.warning("[ CACHE ]: REDIS_URL not configured. Rate limiting is INACTIVE.")
        metrics.increment_counter("redis_not_configured_total")

    if not redis_client:
        logger.warning(
            "[ RATE_LIMITER ] Redis is not configured. "
            "Falling back to in-memory sliding window rate limiter. "
            "This limiter does not persist across restarts and does not "
            "coordinate across multiple worker processes."
        )

    create_db_and_tables()
    
    # [ M-9 ] Automated Alembic Migrations
    if getattr(settings, "APP_ENV", "development") == "production":
        try:
            from alembic import command
            from alembic.config import Config
            alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
            alembic_cfg = Config(alembic_ini_path)
            command.upgrade(alembic_cfg, "head")
            logger.info("[ MIGRATION ]: Alembic successfully synced database schema to head.")
        except Exception as e:
            logger.error(f"[ MIGRATION ]: Alembic upgrade failed: {e}")
    storage_root = os.path.expanduser(settings.POLYTOPE_STORAGE_ROOT)
    vault_root = os.path.join(storage_root, "vaults")
    os.makedirs(vault_root, exist_ok=True)

    # 3. Security Layer
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    sovereign_identity = SovereignIdentity(settings, vault=vault)
    await sovereign_identity.load_keys()
    
    # 3.5. Usage & Cost Analytics (Moved up to support router logging)
    usage_tracker = UsageTracker(db_engine)

    # 4. Inference Layer
    router = ModelRouter(settings, vault=vault, analytics=usage_tracker)
    scanner = GuardrailScanner(router)

    # 5. Affective Engine
    ace = AffectiveEngine()

    # 6. Skill Manager
    skill_manager = SkillManager(vault)

    # 7. Persistent H-LSM Memory System
    # Initialize the three-tier Hierarchical Long-Short Manifold manager.
    # L0 backed by Redis (if available), L1 by SQL, L2 by ChromaDB.

    # Build ChromaDB collection for L2 semantic tier
    chroma_collection = None
    lite_mode = getattr(settings, "LITE_MODE", False)
    if not lite_mode:
        try:
            import chromadb
            persist_dir = os.path.join(os.path.expanduser(settings.POLYTOPE_STORAGE_ROOT), "memory")
            os.makedirs(persist_dir, mode=0o700, exist_ok=True)
            chroma_client = chromadb.PersistentClient(path=persist_dir)
            chroma_collection = chroma_client.get_or_create_collection(
                name="hlsm_semantic",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"[ HLSM ] ChromaDB L2 collection initialized at {persist_dir}")
        except ImportError:
            logger.warning("[ HLSM ] chromadb not found — L2 semantic tier disabled")
        except Exception as e:
            logger.error(f"[ HLSM ] ChromaDB initialization failed: {e} — L2 disabled")

    # Instantiate the H-LSM manager
    hlsm_manager = HLSMManager(
        db_engine=db_engine,
        redis_client=redis_client,       # None if Redis unavailable — L0 falls back to SQL
        chroma_collection=chroma_collection,
        settings=settings,
    )

    # Start the background consolidation loop
    await hlsm_manager.start_consolidation_loop()

    # Backwards-compat: assign to `memory` so existing code still works
    memory = hlsm_manager
    logger.info("[ HLSM ] H-LSM memory system online: L0+L1+L2 active")

    # 8. Usage & Cost Analytics (Assigned above)
    # usage_tracker = UsageTracker(db_engine)

    # 9. Communication & Approval Layers (Injected into Orchestrator)
    ws_gw = JsonRpcGateway(jwt_secret=settings.JWT_SECRET_KEY)
    exec_approval = ExecApprovalManager(db_engine, ws_gateway=ws_gw)

    # 10. Executive Orchestrator
    assert ExecutiveOrchestrator is not None, "Fatal: ExecutiveOrchestrator failed to import"
    orchestrator = ExecutiveOrchestrator(
        router=router,
        vault=vault,
        ace=ace,
        skill_manager=skill_manager,
        analytics=usage_tracker,
        settings=settings,
        vault_root=vault_root,
        approval_manager=exec_approval,
        memory_manager=memory,          # Legacy compat
        hlsm_manager=hlsm_manager,      # H-LSM (new)
    )

    # 11. Task Manager
    task_manager = TaskManager()

    # 12. Local Inference Bridge
    local_inference = LocalInferenceBridge(settings)
    
    # Wire references
    orchestrator.ws_gateway = ws_gw
    router.ws_gateway = ws_gw
    orchestrator.executor.approval_manager = exec_approval

    # Register HLSMMemoryAdapter (replaces the old MemoryAdapter)
    from backend.adapters.memory_adapter import HLSMMemoryAdapter
    orchestrator.adapter_registry.register(HLSMMemoryAdapter(hlsm_manager))
    logger.info("[ ADAPTERS ] HLSMMemoryAdapter registered — hlsm_search/hlsm_store/hlsm_recall tools active.")

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
    oauth_refresh_config = {
        "slack":       {"token_url": "https://slack.com/api/tooling.tokens.rotate",
                        "client_id": getattr(settings,"SLACK_CLIENT_ID",""),
                        "client_secret": getattr(settings,"SLACK_CLIENT_SECRET","")},
        "discord":     {"token_url": "https://discord.com/api/oauth2/token",
                        "client_id": getattr(settings,"DISCORD_CLIENT_ID",""),
                        "client_secret": getattr(settings,"DISCORD_CLIENT_SECRET","")},
        "google_chat": {"token_url": "https://oauth2.googleapis.com/token",
                        "client_id": getattr(settings,"GOOGLE_CLIENT_ID",""),
                        "client_secret": getattr(settings,"GOOGLE_CLIENT_SECRET","")},
        "msteams":     {"token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                        "client_id": getattr(settings,"MSTEAMS_CLIENT_ID",""),
                        "client_secret": getattr(settings,"MSTEAMS_CLIENT_SECRET","")},
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

    # 20b. Wire H-LSM into HeartbeatDaemon for log_only and pcl_signal actions
    if orchestrator and orchestrator.heartbeat and hlsm_manager:
        orchestrator.heartbeat.inject_hlsm(hlsm_manager, router=router, settings=settings)
        logger.info("[ HB ] H-LSM injected into HeartbeatDaemon")

    # 21. Background Services
    await orchestrator.start_background_services()

    # 22. Proactive Cognition Loop (PCL)
    pcl = ProactiveCognitionLoop(
        db_engine=db_engine,
        orchestrator=orchestrator,
        ace_engine=ace,
        goal_engine=goal_engine,
        hlsm_manager=hlsm_manager,
        ws_gateway=ws_gw,
        channel_registry=channel_registry,
        settings=settings,
    )
    await pcl.start()
    logger.info("[ PCL ] Proactive Cognition Loop running.")

    logger.info("[ SERVICES ] All core systems actualized.")

async def _init_channels(vault_root: str):
    assert vault is not None, "Vault must be initialized"
    from backend.bridges.telegram import TelegramBridge
    from backend.bridges.whatsapp import WhatsAppBridge
    from backend.bridges.discord import DiscordBridge
    from backend.bridges.slack import SlackBridge
    from backend.bridges.email import EmailBridge
    from backend.bridges.signal import SignalBridge
    from backend.bridges.google_chat import GoogleChatBridge
    from backend.bridges.nostr import NostrBridge
    from backend.bridges.imessage import IMessageBridge
    from backend.bridges.instagram import InstagramBridge
    from backend.bridges.facebook import FacebookBridge
    from backend.bridges.x_twitter import XBridge
    from backend.bridges.msteams import MSTeamsBridge
    from backend.bridges.wechat import WeChatBridge
    from backend.bridges.iwatch import IWatchBridge
    from backend.bridges.icloud import ICloudBridge
    from backend.bridges.gmail import GmailBridge
    from backend.bridges.gdrive import GDriveBridge
    from backend.bridges.webchat import WebChatBridge
    from backend.bridges.iphone import IPhoneBridge
    from backend.bridges.verus_wallet import VerusWalletBridge

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
    channel_registry["iphone"] = IPhoneBridge("iphone", vault_root, vault_manager=vault)
    channel_registry["verus_wallet"] = VerusWalletBridge("verus_wallet", vault_root, vault_manager=vault)

    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "on_event"):
            adapter.on_event = broadcast_bridge_event
        if hasattr(adapter, "on_inbound") and orchestrator is not None:
            adapter.on_inbound = orchestrator.handle_inbound_message

    # Auto-connect channels
    for ch_name, adapter in channel_registry.items():
        try:
            # 1. Check if enabled (default True)
            enabled_state = await vault.retrieve_secret(f"channel_{ch_name}_enabled")
            adapter.enabled = enabled_state.get("enabled", True) if enabled_state else True
            if not adapter.enabled: continue

            # 1.5 Auto-connect native/local bridges that don't need OAuth
            if ch_name in ["imessage"]:
                success = await adapter.connect({})
                if success:
                    logger.info(f"[ CHANNELS ] Auto-connected native bridge: {ch_name}")
                continue

            if ch_name == "email":
                import os
                icloud_email = os.environ.get("ICLOUD_EMAIL")
                icloud_password = os.environ.get("ICLOUD_APP_PASSWORD")
                if icloud_email and icloud_password:
                    creds = {
                        "email": icloud_email,
                        "password": icloud_password,
                        "imap_server": "imap.mail.me.com",
                        "imap_port": 993,
                        "smtp_server": "smtp.mail.me.com",
                        "smtp_port": 587
                    }
                    success = await adapter.connect(creds)
                    if success:
                        logger.info(f"[ CHANNELS ] Auto-connected iCloud email bridge: {icloud_email}")
                    continue

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
    if hlsm_manager:
        await hlsm_manager.stop_consolidation_loop()
        logger.info("[ HLSM ] Consolidation loop stopped")
    if pcl:
        await pcl.stop()
        logger.info("[ PCL ] Proactive Cognition Loop stopped")
    if cron_engine: await cron_engine.stop()
    if orchestrator: await orchestrator.stop_background_services()
    if updater: await updater.stop()
    
    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "disconnect"):
            await adapter.disconnect()
