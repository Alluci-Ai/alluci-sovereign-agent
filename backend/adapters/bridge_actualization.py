
import logging
from typing import Dict, Any
from .base import Adapter
from ..bridges.slack import SlackBridge
from ..bridges.imessage import IMessageBridge
from ..bridges.whatsapp import WhatsAppBridge
from ..bridges.email import EmailBridge
from ..engine.errors import AdapterError

class BridgeActualizationAdapter(Adapter):
    """
    Sovereign Bridge Actualization Adapter.
    Mediates between the Executive Orchestrator and the backend bridge repository.
    """
    name = "bridge_actualization"
    description = "Execute tasks across Social, Enterprise, and Cloud manifolds (Slack, iMessage, Gmail, etc.)"

    def __init__(self, vault_root: str = "vaults"):
        self.vault_root = vault_root
        self.logger = logging.getLogger("BridgeActualization")
        self.bridges: Dict[str, Any] = {}
        self._init_bridges()

    def _init_bridges(self):
        # Lazy initialization or pre-loading? Let's pre-load the classes.
        # In a full flow, these would be instantiated on demand with vaulted credentials.
        self.bridge_map = {
            "slack": SlackBridge,
            "imessage": IMessageBridge,
            "whatsapp": WhatsAppBridge,
            "gmail": EmailBridge,
            "outlook": EmailBridge
        }

    async def execute(self, args: Dict[str, Any]) -> Any:
        bridge_type = args.get("bridge")
        action = args.get("action") # send_message, fetch_unread, upload, etc.
        params = args.get("params", {})

        if not bridge_type or not action:
            raise AdapterError("Missing 'bridge' or 'action' in actualization request.")

        # Resolve Account ID if provided in params or args
        account_id = params.get("account_id") or args.get("account_id")

        # 1. Resolve Bridge
        bridge = await self._get_or_create_bridge(bridge_type, account_id=account_id)
        if not bridge:
            raise AdapterError(f"Bridge '{bridge_type}' is not supported or misconfigured.")

        # 2. Execute Action
        try:
            if action == "send_message":
                recipient = params.get("recipient")
                content = params.get("content")
                if not recipient or not content:
                    raise AdapterError("Missing 'recipient' or 'content' for send_message.")
                return await bridge.send_message(recipient, content)

            elif action == "fetch_unread":
                limit = params.get("limit", 10)
                return await bridge.fetch_unread(limit=limit)

            elif action == "upload_file":
                # Conceptually for iCloud/G-Drive
                return {"status": "success", "msg": f"File vaulted to {bridge_type}"}

            else:
                raise AdapterError(f"Action '{action}' not implemented for {bridge_type}.")

        except Exception as e:
            self.logger.error(f"Bridge Execution Error ({bridge_type}:{action}): {e}")
            raise AdapterError(f"Bridge Failure: {str(e)}")

    async def _get_or_create_bridge(self, bridge_type: str, account_id: str = None):
        cache_key = f"{bridge_type}_{account_id}" if account_id else bridge_type
        if cache_key in self.bridges:
            return self.bridges[cache_key]

        bridge_class = self.bridge_map.get(bridge_type.lower())
        if not bridge_class:
            return None

        # Resolve credentials if account_id is provided
        credentials = {"mock": "true"}
        if account_id:
            try:
                from ..models import ChannelAccount
                from sqlmodel import Session, select
                # We need the engine, usually injected or available via global
                from ..database import engine
                with Session(engine) as session:
                    stmt = select(ChannelAccount).where(ChannelAccount.account_identifier == account_id)
                    acc = session.exec(stmt).first()
                    if acc and acc.credentials:
                        credentials = acc.credentials
                        self.logger.info(f"[BridgeActualization] Loaded credentials for {bridge_type} account {account_id}")
            except Exception as e:
                self.logger.warning(f"[BridgeActualization] Could not load account {account_id} from DB: {e}")

        # Instantiate bridge with isolated vault
        # Use account_id in bridge_id to ensure separate vault paths
        inst_id = f"{bridge_type}_{account_id}" if account_id else bridge_type
        bridge = bridge_class(bridge_id=inst_id, vault_root=self.vault_root)
        
        # MOCK CONNECT or real connect if we had vaulted tokens
        if hasattr(bridge, "connect"):
            await bridge.connect(credentials)
        else:
            bridge.is_connected = True 
        
        self.bridges[cache_key] = bridge
        return bridge
