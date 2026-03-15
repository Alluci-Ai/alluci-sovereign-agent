
import httpx
import logging
from ..logging_config import get_logger
from typing import Any, Dict, List, Optional
from backend.config import settings

logger = get_logger("VerusRPC")

class VerusRPCClient:
    """
    Async client for communicating with the verusd daemon via JSON-RPC.
    Covers: wallet, identity, DeFi, mining/staking, and Ethereum bridge operations.
    """
    def __init__(self):
        self.local_url = f"http://{settings.VERUS_RPC_HOST}:{settings.VERUS_RPC_PORT}"
        self.public_url = settings.VERUS_PUBLIC_RPC_URL
        self.auth = None
        if settings.VERUS_RPC_USER and settings.VERUS_RPC_PASSWORD:
            self.auth = (settings.VERUS_RPC_USER, settings.VERUS_RPC_PASSWORD)
        
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _call(self, method: str, params: List[Any] = [], use_public: bool = False) -> Any:
        # Determine URL and Auth
        target_url = self.public_url if (use_public or settings.VERUS_LITE_MODE) else self.local_url
        auth = None if (use_public or settings.VERUS_LITE_MODE) else self.auth

        payload = {
            "jsonrpc": "1.0",
            "id": "alluci-agent",
            "method": method,
            "params": params
        }
        try:
            response = await self.client.post(
                target_url, 
                json=payload, 
                auth=auth,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            if result.get("error"):
                # If local fails and we aren't already forcing public, try public fallback for read-only methods
                if not use_public and not settings.VERUS_LITE_MODE and method in ["getinfo", "getcurrency", "getidentity", "getaddressbalance"]:
                    logger.warning(f"Local RPC failed for {method}, falling back to public.")
                    return await self._call(method, params, use_public=True)
                
                logger.error(f"Verus RPC Error [{method}]: {result['error']}")
                raise Exception(f"Verus RPC Error: {result['error']}")
            return result.get("result")
        except (httpx.HTTPStatusError, httpx.ConnectError) as e:
            # Automatic fallback to public for specific safe methods if local is down
            if not use_public and not settings.VERUS_LITE_MODE and method in ["getinfo", "getcurrency", "getidentity", "getaddressbalance"]:
                logger.warning(f"Local RPC unreachable for {method}, falling back to public.")
                return await self._call(method, params, use_public=True)
            logger.error(f"Verus RPC Connection Error [{method}]: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Verus RPC Unexpected Error [{method}]: {str(e)}")
            raise

    # ── Identity Methods ──────────────────────────────────────────────────

    async def get_identity(self, name_or_iaddr: str) -> Dict[str, Any]:
        """Calls getidentity RPC."""
        return await self._call("getidentity", [name_or_iaddr])

    async def sign_message(self, identity: str, message: str) -> str:
        """Calls signmessage RPC."""
        return await self._call("signmessage", [identity, message])

    async def verify_message(self, identity: str, signature: str, message: str) -> bool:
        """Calls verifymessage RPC."""
        return await self._call("verifymessage", [identity, signature, message])

    async def update_identity(self, identity_json: Dict[str, Any]) -> str:
        """Calls updateidentity RPC. Requires funded wallet for fees."""
        return await self._call("updateidentity", [identity_json])

    async def register_name_commitment(self, name: str, controlling_address: str, referral: str = "") -> Dict[str, Any]:
        """Calls registernamecommitment RPC — first step of VerusID creation."""
        params = [name, controlling_address]
        if referral:
            params.append(referral)
        return await self._call("registernamecommitment", params)

    async def register_identity(self, commitment: Dict[str, Any]) -> str:
        """Calls registeridentity RPC — completes VerusID registration."""
        return await self._call("registeridentity", [commitment])

    async def revoke_identity(self, name_or_iaddr: str) -> str:
        """Calls revokeidentity RPC."""
        return await self._call("revokeidentity", [name_or_iaddr])

    async def recover_identity(self, name_or_iaddr: str) -> str:
        """Calls recoveridentity RPC."""
        return await self._call("recoveridentity", [name_or_iaddr])

    async def set_identity_timelock(self, identity: str, locktime: int, flags: int = 2) -> str:
        """Locks a VerusID (Verus Vault) via updateidentity with timelock."""
        return await self._call("updateidentity", [{
            "name": identity,
            "flags": flags,
            "timelock": locktime
        }])

    async def get_content_multimap(self, identity: str, key: str = "") -> Dict[str, Any]:
        """Helper to specifically extract VDXF contentmultimap data."""
        identity_data = await self.get_identity(identity)
        content_map = identity_data.get("identity", {}).get("contentmultimap", {})
        if key:
            return content_map.get(key, [])
        return content_map

    # ── Wallet Core Methods ───────────────────────────────────────────────

    async def get_balance(self, account: str = "*", min_conf: int = 1) -> float:
        """Returns total confirmed balance."""
        return await self._call("getbalance", [account, min_conf])

    async def get_currency_balance(self, address: str) -> Dict[str, float]:
        """Returns per-currency balance for an address."""
        return await self._call("getcurrencybalance", [address])

    async def get_unconfirmed_balance(self) -> float:
        """Returns the total unconfirmed balance."""
        return await self._call("getunconfirmedbalance", [])

    async def list_unspent(self, min_conf: int = 1, max_conf: int = 9999999, addresses: Optional[List[str]] = None) -> List[Dict]:
        """Lists unspent transaction outputs (UTXOs)."""
        params: List[Any] = [min_conf, max_conf]
        if addresses:
            params.append(addresses)
        return await self._call("listunspent", params)

    async def list_transactions(self, account: str = "*", count: int = 50, skip: int = 0) -> List[Dict]:
        """Lists recent transactions."""
        return await self._call("listtransactions", [account, count, skip])

    async def get_transaction(self, txid: str) -> Dict[str, Any]:
        """Gets detailed information about a transaction."""
        return await self._call("gettransaction", [txid])

    async def send_to_address(self, address: str, amount: float, comment: str = "", comment_to: str = "") -> str:
        """Sends VRSC to an address. Returns txid."""
        return await self._call("sendtoaddress", [address, amount, comment, comment_to])

    async def send_currency(self, from_address: str, outputs: List[Dict[str, Any]], min_conf: int = 1, fee_amount: float = 0.0001) -> str:
        """
        Advanced multi-currency send via sendcurrency RPC.
        Supports currency conversion, cross-chain sends, and bridge operations.
        
        Each output dict can contain:
          - address, amount, currency
          - convertto, via (for DeFi conversions)
          - exportto (for cross-chain/bridge)
          - memo (for shielded)
        """
        params: List[Any] = [from_address, outputs, min_conf, fee_amount]
        return await self._call("sendcurrency", params)

    async def get_new_address(self) -> str:
        """Generates a new transparent receiving address."""
        return await self._call("getnewaddress", [])

    async def get_addresses_by_account(self, account: str = "") -> List[str]:
        """Lists all addresses for an account."""
        return await self._call("getaddressesbyaccount", [account])

    async def validate_address(self, address: str) -> Dict[str, Any]:
        """Validates a Verus address and returns metadata."""
        return await self._call("validateaddress", [address])

    async def get_wallet_info(self) -> Dict[str, Any]:
        """Returns wallet-level info (balance, txcount, keypoolsize)."""
        return await self._call("getwalletinfo", [])

    # ── Shielded (z-address) Methods ──────────────────────────────────────

    async def z_get_balance(self, address: str, min_conf: int = 1) -> float:
        """Returns the balance of a z-address (shielded)."""
        return await self._call("z_getbalance", [address, min_conf])

    async def z_get_new_address(self) -> str:
        """Generates a new shielded z-address."""
        return await self._call("z_getnewaddress", [])

    async def z_send_many(self, from_address: str, amounts: List[Dict[str, Any]], min_conf: int = 1, fee: float = 0.0001) -> str:
        """Sends from a z-address. Returns an operation ID (async)."""
        return await self._call("z_sendmany", [from_address, amounts, min_conf, fee])

    async def z_get_operation_result(self, op_ids: Optional[List[str]] = None) -> List[Dict]:
        """Checks the result of async z-operations."""
        return await self._call("z_getoperationresult", [op_ids or []])

    async def z_list_addresses(self) -> List[str]:
        """Lists all shielded addresses in the wallet."""
        return await self._call("z_listaddresses", [])

    # ── DeFi & Currency Methods ───────────────────────────────────────────

    async def get_currency(self, currency_name: str) -> Dict[str, Any]:
        """Gets full currency definition (reserves, supply, options)."""
        return await self._call("getcurrency", [currency_name])

    async def get_currency_converters(self, currencies: Optional[List[str]] = None) -> List[Dict]:
        """Finds AMM basket currencies that can convert the given currencies."""
        return await self._call("getcurrencyconverters", [currencies or []])

    async def define_currency(self, definition: Dict[str, Any]) -> str:
        """Defines a new token or basket currency. Requires a VerusID."""
        return await self._call("definecurrency", [definition])

    async def get_offers(self, currency: str, is_buy: bool = True, with_tx: bool = False) -> List[Dict]:
        """Lists open marketplace offers for a currency."""
        return await self._call("getoffers", [currency, is_buy, with_tx])

    async def make_offer(self, from_address: str, offer: Dict[str, Any], return_tx: bool = False) -> str:
        """Creates a marketplace offer (order book)."""
        return await self._call("makeoffer", [from_address, offer, return_tx])

    # ── Mining & Staking Methods ──────────────────────────────────────────

    async def set_generate(self, generate: bool, num_threads: int = 0) -> None:
        """
        Controls mining/staking:
          setgenerate true 1  → mine with 1 thread
          setgenerate true 0  → stake only
          setgenerate false   → stop all
        """
        return await self._call("setgenerate", [generate, num_threads])

    async def get_mining_info(self) -> Dict[str, Any]:
        """Returns mining info: hashrate, difficulty, blocks, staking status."""
        return await self._call("getmininginfo", [])

    async def get_generate(self) -> bool:
        """Returns whether the node is currently generating (mining/staking)."""
        return await self._call("getgenerate", [])

    async def get_block_template(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Returns block template for advanced mining."""
        return await self._call("getblocktemplate", [params or {}])

    # ── Blockchain Info Methods ───────────────────────────────────────────

    async def get_blockchain_info(self) -> Dict[str, Any]:
        """Returns general blockchain info (chain, blocks, difficulty, etc.)."""
        return await self._call("getblockchaininfo", [])

    async def get_info(self) -> Dict[str, Any]:
        """Returns general daemon info (version, blocks, connections, balance)."""
        return await self._call("getinfo", [])

    async def get_address_balance(self, addresses: List[str]) -> Dict[str, Any]:
        """Returns balance and currencybalance for a list of addresses (requires addressindex)."""
        return await self._call("getaddressbalance", [{"addresses": addresses}])

    # ── Cross-Chain & Bridge Methods ──────────────────────────────────────

    async def get_cross_chain_export(self, txid: str) -> Dict[str, Any]:
        """Checks status of a cross-chain export transaction."""
        return await self._call("getcrosschain export", [txid])

    async def get_pending_transfers(self, currency: str = "") -> List[Dict]:
        """Lists pending cross-chain transfers."""
        params = [currency] if currency else []
        return await self._call("getpendingtransfers", params)

    async def close(self):
        await self.client.aclose()

# Singleton instance
verus_rpc = VerusRPCClient()
