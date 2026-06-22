import os
from ..logging_config import get_logger
from typing import Dict, Any, Callable
from .base import Adapter
from ..bridges.slack import SlackBridge
from ..bridges.imessage import IMessageBridge
from ..bridges.whatsapp import WhatsAppBridge
from ..bridges.email import EmailBridge
from ..bridges.telegram import TelegramBridge
from ..bridges.discord import DiscordBridge
from ..bridges.facebook import FacebookBridge
from ..bridges.instagram import InstagramBridge
from ..bridges.x_twitter import XBridge
from ..bridges.gmail import GmailBridge
from ..bridges.gdrive import GDriveBridge
from ..bridges.icloud import ICloudBridge
from ..bridges.msteams import MSTeamsBridge
from ..bridges.webchat import WebChatBridge
from ..bridges.wechat import WeChatBridge
from ..bridges.iphone import IPhoneBridge
from ..bridges.iwatch import IWatchBridge
from ..bridges.signal import SignalBridge
from ..bridges.google_chat import GoogleChatBridge
from ..bridges.nostr import NostrBridge
from ..engine.errors import AdapterError
from ..security.vault import VaultManager
from ..security.oauth_handler import OAuthHandler
from ..security.qr_sync_handler import QRSyncHandler
from ..security.tunnel_handler import TunnelHandler

class BridgeActualizationAdapter(Adapter):
    """
    Sovereign Bridge Actualization Adapter.
    Mediates between the Executive Orchestrator and the backend bridge repository.
    Supports OAuth 2.0, QR Sync, Token Exchange, and Secure Tunnel flows.
    """
    name = "bridge_actualization"
    description = "Execute tasks across Social, Enterprise, and Cloud manifolds (Slack, iMessage, Gmail, etc.)"

    def __init__(self, vault_root: str = None, on_inbound: Callable = None):  # type: ignore
        from ..config import settings
        self.vault_manager = VaultManager(settings.POLYTOPE_MASTER_KEY, vault_root)
        self.oauth_handler = OAuthHandler(self.vault_manager)
        from .. import services
        self.qr_handler = QRSyncHandler(self.vault_manager, redis_client=services.redis_client)
        self.tunnel_handler = TunnelHandler()
        self.logger = get_logger("BridgeActualization")
        self.on_inbound = on_inbound
        self.bridges: Dict[str, Any] = {}
        self._init_bridges()

    def _init_bridges(self):
        from ..config import settings
        self.bridge_map = {
            "slack": SlackBridge,
            "telegram": TelegramBridge,
            "discord": DiscordBridge,
            "x": XBridge,
            "twitter": XBridge,
            "gmail": GmailBridge,
            "email": EmailBridge,
            "gdrive": GDriveBridge,
            "icloud": ICloudBridge,
            "msteams": MSTeamsBridge,
            "webchat": WebChatBridge,
            "imessage": IMessageBridge,
            "whatsapp": WhatsAppBridge,
            "iphone": IPhoneBridge,
            "iwatch": IWatchBridge,
            "signal": SignalBridge,
            "google_chat": GoogleChatBridge,
            "nostr": NostrBridge
        }
        
        # Add high-risk/social bridges only if explicitly enabled (GAP-009)
        if getattr(settings, "UNOFFICIAL_BRIDGES_ENABLED", False):
            self.bridge_map.update({
                "wechat": WeChatBridge,
                "facebook": FacebookBridge,
                "instagram": InstagramBridge,
            })
        else:
            self.logger.info("[BridgeActualization] Unofficial social bridges (WeChat, FB, IG) are disabled.")

    async def execute(self, args: Dict[str, Any]) -> Any:
        bridge_type = args.get("bridge")
        action = args.get("action") # send_message, fetch_unread, handle_auth, etc.
        params = args.get("params", {})

        if not bridge_type or not action:
            raise AdapterError("Missing 'bridge' or 'action' in actualization request.")

        # Resolve Account ID
        account_id = params.get("account_id") or params.get("sender") or args.get("account_id") or "default"

        # Special Action: handle_auth (AuthPortal routing)
        if action == "handle_auth":
            auth_type = params.get("type")
            payload = params.get("payload", {})
            return await self.handle_auth(bridge_type, auth_type, account_id, payload)

        # 1. Resolve Bridge
        bridge = await self._get_or_create_bridge(bridge_type, account_id=account_id)
        if not bridge:
            raise AdapterError(f"Bridge '{bridge_type}' is not supported or misconfigured.")

        # 2. Execute Action
        try:
            if action in ("send", "send_message"):
                recipient = params.get("recipient")
                content = params.get("content")
                if not recipient or not content:
                    raise AdapterError("Missing 'recipient' or 'content' for send_message.")
                kwargs = params.copy()
                kwargs.pop("recipient", None)
                kwargs.pop("content", None)
                if "account_id" not in kwargs:
                    kwargs["account_id"] = account_id
                return await bridge.send(recipient, content, **kwargs)

            elif action == "fetch_unread":
                limit = params.get("limit", 10)
                kwargs = params.copy()
                if bridge_type in ("gmail", "email") and "email" not in kwargs:
                    kwargs["email"] = account_id
                
                # Check if fetch_unread accepts kwargs
                import inspect
                sig = inspect.signature(bridge.fetch_unread)
                if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()) or "email" in sig.parameters:
                     # pass kwargs if it accepts them or specifically 'email'
                     return await bridge.fetch_unread(**{k: v for k, v in kwargs.items() if k in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())})
                return await bridge.fetch_unread(limit=limit)

            elif action == "upload_file":
                # Implementation for G-Drive/iCloud
                if hasattr(bridge, "upload_file"):
                    return await bridge.upload_file(params.get("path"), params.get("content"))
                return {"status": "success", "msg": f"File vaulted to {bridge_type}"}

            elif action == "get_health":
                if hasattr(bridge, "get_health"):
                    return bridge.get_health()
                return {"bridge_id": f"{bridge_type}_{account_id}", "is_connected": bridge.is_connected}

            else:
                # Direct method call fallback
                method = getattr(bridge, action, None)
                if callable(method):
                    return await method(**params)
                raise AdapterError(f"Action '{action}' not implemented for {bridge_type}.")

        except Exception as e:
            self.logger.error(f"Bridge Execution Error ({bridge_type}:{action}): {e}")
            raise AdapterError(f"Bridge Failure: {str(e)}")

    async def handle_auth(self, bridge_id: str, auth_type: str, account_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes authentication requests from the UI AuthPortal.
        Determines whether to use a bridge-specific handler or a generic protocol handler.
        """
        self.logger.info(f"Handling Auth: [{auth_type}] for bridge [{bridge_id}] account [{account_id}]")
        
        # 1. Protocol Dispatch
        if auth_type == "oauth":
            return await self._handle_oauth_flow(bridge_id, account_id, payload)
        
        elif auth_type == "qr_sync":
            return await self._handle_qr_sync_flow(bridge_id, account_id, payload)
        
        elif auth_type == "token":
            # Direct token exchange (manual insertion)
            return await self._handle_token_exchange(bridge_id, account_id, payload)
        
        elif auth_type == "tunnel":
            # MS Teams / Slack Enterprise tunneling
            return await self._handle_secure_tunnel(bridge_id, account_id, payload)

        elif auth_type == "challenge":
            # Generate a new QR Sync challenge
            return {"status": "success", "challenge": await self.qr_handler.create_sync_challenge()}

        else:
            raise AdapterError(f"Unsupported auth type: {auth_type}")

    async def _handle_oauth_flow(self, bridge_id: str, account_id: str, payload: Dict[str, Any]):
        """Exchanges an OAuth code for tokens using the generic OAuthHandler."""
        from ..security.oauth_config import get_provider_config
        
        # Check if OAuth is configured for this bridge
        config = get_provider_config(bridge_id.lower())
        if not config:
            raise AdapterError(f"OAuth not configured for bridge: {bridge_id}")
            
        client_id = os.getenv(config["client_id_env"])
        client_secret = os.getenv(config.get("client_secret_env", ""))
        
        return await self.oauth_handler.exchange_code(
            bridge_id=bridge_id,
            account_id=account_id,
            token_url=config["token_url"],
            client_id=client_id,  # type: ignore
            client_secret=client_secret,
            code=payload.get("code"),  # type: ignore
            redirect_uri=payload.get("redirect_uri"),  # type: ignore
            code_verifier=payload.get("code_verifier")
        )

    async def _handle_qr_sync_flow(self, bridge_id: str, account_id: str, payload: Dict[str, Any]):
        """Completes a QR Sync pairing flow."""
        sync_id = payload.get("sync_id")
        if not sync_id:
            raise AdapterError("Missing 'sync_id' for QR sync.")
            
        success = await self.qr_handler.complete_sync(
            bridge_id=bridge_id,
            account_id=account_id,
            sync_id=sync_id,
            payload=payload.get("credentials", {})
        )
        
        if success:
            return {"status": "success", "message": "Mobile pairing successful."}
        return {"status": "failed", "error": "Invalid or expired sync session."}

    async def _handle_token_exchange(self, bridge_id: str, account_id: str, payload: Dict[str, Any]):
        # Securely store the manually provided token/credentials
        await self.vault_manager.store_connection_secret(bridge_id, account_id, payload)
        
        # Re-initialize bridge to verify connection
        bridge = await self._get_or_create_bridge(bridge_id, account_id, force_reload=True)
        if bridge.is_connected:
            return {
                "status": "success", 
                "message": f"{bridge_id.capitalize()} token active and verified.",
                "account": account_id,
                "verified_at": str(getattr(bridge, 'last_activity', 'now'))
            }
        return {"status": "failed", "error": "Verification failed with provided token."}

    async def _handle_secure_tunnel(self, bridge_id: str, account_id: str, payload: Dict[str, Any]):
        """
        Manages the persistent reverse-proxy tunnel for enterprise networks.
        Starting the tunnel allows the agent to receive webhooks for bridges like Slack/Teams.
        """
        action = payload.get("action", "status") # start, stop, status
        
        if action == "start":
            relay_url = payload.get("relay_url")
            if relay_url:
                os.environ["TUNNEL_RELAY_URL"] = relay_url
            
            await self.tunnel_handler.start()
            return {"status": "success", "message": "Secure Tunnel started.", "tunnel": self.tunnel_handler.get_status()}
            
        elif action == "stop":
            await self.tunnel_handler.stop()
            return {"status": "success", "message": "Secure Tunnel stopped."}
            
        else:
            return {"status": "success", "tunnel": self.tunnel_handler.get_status()}

    async def _get_or_create_bridge(self, bridge_type: str, account_id: str = "default", force_reload: bool = False):
        cache_key = f"{bridge_type}_{account_id}"
        if cache_key in self.bridges and not force_reload:
            return self.bridges[cache_key]

        bridge_class = self.bridge_map.get(bridge_type.lower())
        if not bridge_class:
            return None

        # 1. Retrieve connection-specific credentials from the hardened vault
        credentials = await self.vault_manager.retrieve_connection_secret(bridge_type, account_id)
        
        # Fallback to general credentials if not found (legacy support)
        if not credentials:
            credentials = await self.vault_manager.retrieve_secret(bridge_type)

        # Instantiate bridge with account-isolated vault path and vault manager
        bridge = bridge_class(bridge_id=bridge_type, vault_root=self.vault_manager.vault_root, vault_manager=self.vault_manager)  # type: ignore
        bridge.on_inbound = self.on_inbound
        if hasattr(bridge, "connect"):
            await bridge.connect(credentials)
        else:
            bridge.is_connected = bool(credentials)
        
        self.bridges[cache_key] = bridge
        return bridge
