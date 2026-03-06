"""
Verus Wallet Service — High-level wallet operations for the Alluci Sovereign Agent.

Wraps VerusRPCClient with business logic, error handling, and response formatting.
The agent's VerusID (from config) is used as the primary signing authority.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.security.verus_rpc import verus_rpc
from backend.config import settings
from backend.models import WalletDashboard, CurrencyBalance

logger = logging.getLogger("VerusWallet")


class VerusWalletService:
    """
    Business logic layer for Verus wallet operations.
    All methods are async and communicate with verusd via VerusRPCClient.
    """

    def __init__(self):
        self.rpc = verus_rpc
        self.identity = settings.VERUS_ID_IDENTITY  # e.g., "Alluci@"

    def set_identity(self, identity: str):
        """Sets the active VerusID for the wallet service."""
        # Normalize identity (append @ if missing for VerusID names)
        if identity and not identity.endswith("@") and not identity.startswith("i"):
             identity += "@"
        self.identity = identity
        logger.info(f"[Wallet] Active Identity set to: {identity}")

    # ── Dashboard ─────────────────────────────────────────────────────────

    async def get_dashboard(self) -> WalletDashboard:
        """
        Returns a comprehensive wallet dashboard snapshot:
        balances, identity info, mining status, recent transactions.
        """
        dashboard_data: Dict[str, Any] = {
            "connected": False,
            "identity": None,
            "balances": [],
            "total_vrsc": 0.0,
            "unconfirmed": 0.0,
            "mining": None,
            "recent_transactions": [],
            "blockchain": None,
            "pbaas_chains": settings.VERUS_PBAAS_CHAINS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Check daemon connectivity
            try:
                info = await self.rpc.get_info()
                dashboard_data["connected"] = True
                dashboard_data["blockchain"] = {
                    "chain": info.get("name", "VRSC"),
                    "blocks": info.get("blocks", 0),
                    "connections": info.get("connections", 0),
                    "version": info.get("version", 0),
                    "synced": info.get("longestchain", 0) == info.get("blocks", 0),
                }
            except Exception:
                # If we are in Lite mode, getinfo might still work via public RPC
                if settings.VERUS_LITE_MODE:
                    info = await self.rpc.get_info()
                    dashboard_data["connected"] = True
                    dashboard_data["blockchain"] = {
                        "chain": info.get("name", "VRSC"),
                        "blocks": info.get("blocks", 0),
                        "connections": info.get("connections", 0),
                        "version": info.get("version", 0),
                        "synced": True, # Public nodes are usually synced
                    }

            if not dashboard_data["connected"]:
                logger.warning("[Wallet] Daemon not reachable and not in Lite mode.")
                return WalletDashboard(**dashboard_data)

        except Exception as e:
            logger.warning(f"[Wallet] connectivity check failed: {e}")
            return WalletDashboard(**dashboard_data)

        try:
            # Balances
            if settings.VERUS_LITE_MODE and self.identity:
                # In Lite Mode, query public identity balance
                id_data = await self.rpc.get_identity(self.identity)
                i_addr = id_data.get("identity", {}).get("identityaddress")
                if i_addr:
                    addr_bal = await self.rpc.get_address_balance([i_addr])
                    # Verus address balance returns sats/atomic units
                    dashboard_data["total_vrsc"] = addr_bal.get("balance", 0) / 100000000
                    dashboard_data["balances"] = [
                        CurrencyBalance(currency=k, amount=v) 
                        for k, v in addr_bal.get("currencybalance", {}).items()
                    ]
            else:
                # Normal Mode (Sovereign)
                balance = await self.rpc.get_balance()
                dashboard_data["total_vrsc"] = balance

                unconfirmed = await self.rpc.get_unconfirmed_balance()
                dashboard_data["unconfirmed"] = unconfirmed
                
                # Full balances for breakdown
                full_balances = await self.get_balances()
                dashboard_data["balances"] = [
                    CurrencyBalance(currency=k, amount=v) 
                    for k, v in full_balances.get("currencies", {}).items()
                ]
        except Exception as e:
            logger.error(f"[Wallet] Balance fetch failed: {e}")

        try:
            # Identity info
            if self.identity:
                id_data = await self.rpc.get_identity(self.identity)
                identity_obj = id_data.get("identity", {})
                dashboard_data["identity"] = {
                    "name": identity_obj.get("name", ""),
                    "identityaddress": identity_obj.get("identityaddress", ""),
                    "status": id_data.get("status", "active"),
                    "flags": identity_obj.get("flags", 0),
                    "minimumsignatures": identity_obj.get("minimumsignatures", 1),
                    "primaryaddresses": identity_obj.get("primaryaddresses", []),
                    "revocationauthority": identity_obj.get("revocationauthority", ""),
                    "recoveryauthority": identity_obj.get("recoveryauthority", ""),
                    "timelock": identity_obj.get("timelock", 0),
                }
        except Exception as e:
            logger.warning(f"[Wallet] Identity fetch failed: {e}")

        try:
            # Mining / staking status
            if not settings.VERUS_LITE_MODE:
                mining_info = await self.rpc.get_mining_info()
                dashboard_data["mining"] = {
                    "generating": mining_info.get("generate", False),
                    "staking": mining_info.get("staking", False),
                    "hashrate": mining_info.get("networkhashps", 0),
                    "local_hashrate": mining_info.get("hashrate", 0) if mining_info.get("generate") else 0,
                    "difficulty": mining_info.get("difficulty", 0),
                    "blocks": mining_info.get("blocks", 0),
                }
            else:
                # In Lite Mode, just show network difficulty/hashrate from getinfo
                dashboard_data["mining"] = {
                    "generating": False,
                    "staking": False,
                    "hashrate": 0,
                    "local_hashrate": 0,
                    "difficulty": 0,
                    "blocks": dashboard_data["blockchain"]["blocks"] if dashboard_data["blockchain"] else 0,
                }
        except Exception as e:
            logger.warning(f"[Wallet] Mining info failed: {e}")

        try:
            # Recent transactions (last 10)
            txs = await self.rpc.list_transactions("*", 10, 0)
            dashboard_data["recent_transactions"] = [
                self._format_transaction(tx) for tx in (txs or [])
            ]
        except Exception as e:
            logger.warning(f"[Wallet] Transaction list failed: {e}")
            dashboard_data["recent_transactions"] = []

        try:
             # Ensure mining is never None for the model
             if dashboard_data["mining"] is None:
                 dashboard_data["mining"] = {
                    "generating": False,
                    "staking": False,
                    "hashrate": 0,
                    "local_hashrate": 0,
                    "difficulty": 0,
                    "blocks": 0
                 }
             
             # Final validation check before returning
             return WalletDashboard(**dashboard_data)
        except Exception as e:
             logger.error(f"[Wallet] Final dashboard assembly failed: {e}")
             # Return a minimal valid dashboard instead of crashing
             return WalletDashboard(
                 connected=dashboard_data.get("connected", False),
                 total_vrsc=dashboard_data.get("total_vrsc", 0.0),
                 unconfirmed=dashboard_data.get("unconfirmed", 0.0),
                 balances=[],
                 recent_transactions=[],
                 pbaas_chains=settings.VERUS_PBAAS_CHAINS,
                 timestamp=datetime.now(timezone.utc).isoformat()
             )

    # ── Balances ──────────────────────────────────────────────────────────

    async def get_balances(self) -> Dict[str, Any]:
        """Returns all currency balances across all addresses."""
        result: Dict[str, Any] = {
            "vrsc": 0.0,
            "unconfirmed": 0.0,
            "currencies": {},
            "addresses": [],
        }

        try:
            if settings.VERUS_LITE_MODE and self.identity:
                # In Lite Mode, query public identity balance
                id_data = await self.rpc.get_identity(self.identity)
                i_addr = id_data.get("identity", {}).get("identityaddress")
                if i_addr:
                    addr_bal = await self.rpc.get_address_balance([i_addr])
                    result["vrsc"] = addr_bal.get("balance", 0) / 100000000
                    result["currencies"] = addr_bal.get("currencybalance", {})
                    result["addresses"] = [{"address": i_addr, "balances": result["currencies"]}]
            else:
                # Normal Mode (Sovereign)
                result["vrsc"] = await self.rpc.get_balance()
                result["unconfirmed"] = await self.rpc.get_unconfirmed_balance()

                # Get multi-currency balances from all addresses
                addresses = await self.rpc.get_addresses_by_account("")
                for addr in (addresses or []):
                    try:
                        balances = await self.rpc.get_currency_balance(addr)
                        if balances:
                            result["addresses"].append({
                                "address": addr,
                                "balances": balances,
                            })
                            for currency, amount in balances.items():
                                result["currencies"][currency] = result["currencies"].get(currency, 0.0) + amount
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"[Wallet] Balance aggregation error: {e}")

        return result

    # ── Transactions ──────────────────────────────────────────────────────

    async def get_transactions(self, count: int = 50, skip: int = 0) -> Dict[str, Any]:
        """Returns paginated transaction history."""
        try:
            txs = await self.rpc.list_transactions("*", count + 1, skip)
            has_more = len(txs or []) > count
            items = (txs or [])[:count]

            return {
                "transactions": [self._format_transaction(tx) for tx in items],
                "count": len(items),
                "skip": skip,
                "has_more": has_more,
            }
        except Exception as e:
            logger.error(f"[Wallet] list transactions: {e}")
            return {"transactions": [], "count": 0, "skip": skip, "has_more": False}

    async def get_transaction_detail(self, txid: str) -> Dict[str, Any]:
        """Returns detailed information about a specific transaction."""
        try:
            tx = await self.rpc.get_transaction(txid)
            return self._format_transaction(tx) if tx else {}
        except Exception as e:
            logger.error(f"[Wallet] get transaction {txid}: {e}")
            return {}

    # ── Send & Receive ────────────────────────────────────────────────────

    async def send(self, to: str, amount: float, currency: str = "VRSC", memo: str = "") -> Dict[str, Any]:
        """
        Sends currency. Uses sendtoaddress for simple VRSC sends,
        sendcurrency for multi-currency operations.
        """
        try:
            if currency.upper() == "VRSC" and not memo:
                txid = await self.rpc.send_to_address(to, amount, memo)
            else:
                output = {"address": to, "amount": amount, "currency": currency}
                if memo:
                    output["memo"] = memo
                txid = await self.rpc.send_currency("*", [output])

            return {"success": True, "txid": txid}
        except Exception as e:
            logger.error(f"[Wallet] send failed: {e}")
            return {"success": False, "error": str(e)}

    async def convert(self, amount: float, from_currency: str, to_currency: str,
                      via: Optional[str] = None, from_address: str = "*") -> Dict[str, Any]:
        """
        DeFi currency conversion via sendcurrency + convertto.
        Optionally routes via a specific basket currency.
        """
        try:
            output: Dict[str, Any] = {
                "address": from_address if from_address != "*" else await self.rpc.get_new_address(),
                "amount": amount,
                "currency": from_currency,
                "convertto": to_currency,
            }
            if via:
                output["via"] = via

            txid = await self.rpc.send_currency(from_address, [output])
            return {"success": True, "txid": txid}
        except Exception as e:
            logger.error(f"[Wallet] convert failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_receive_address(self) -> Dict[str, str]:
        """Generates a new transparent receiving address."""
        try:
            addr = await self.rpc.get_new_address()
            return {"address": addr, "type": "transparent"}
        except Exception as e:
            logger.error(f"[Wallet] new address failed: {e}")
            return {"address": "", "error": str(e)}

    # ── VerusPay Invoice ──────────────────────────────────────────────────

    async def create_invoice(self, amount: float, currency: str = "VRSC",
                             memo: str = "", expiry_minutes: int = 60) -> Dict[str, Any]:
        """
        Creates a VerusPay-compatible invoice with a fresh receiving address.
        Returns data suitable for QR code generation.
        """
        try:
            addr = await self.rpc.get_new_address()
            invoice = {
                "address": addr,
                "amount": amount,
                "currency": currency,
                "memo": memo,
                "expiry_minutes": expiry_minutes,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # VerusPay v2 URI format
                "uri": f"verus:{addr}?amount={amount}&currency={currency}&memo={memo}",
            }
            return {"success": True, "invoice": invoice}
        except Exception as e:
            logger.error(f"[Wallet] Invoice creation failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Mining & Staking ──────────────────────────────────────────────────

    async def get_mining_status(self) -> Dict[str, Any]:
        """Returns current mining/staking status."""
        try:
            info = await self.rpc.get_mining_info()
            generating = await self.rpc.get_generate()
            return {
                "generating": generating,
                "staking": info.get("staking", False),
                "hashrate": info.get("networkhashps", 0),
                "local_hashrate": info.get("hashrate", 0),
                "difficulty": info.get("difficulty", 0),
                "blocks": info.get("blocks", 0),
                "errors": info.get("errors", ""),
            }
        except Exception as e:
            logger.error(f"[Wallet] mining status: {e}")
            return {"generating": False, "staking": False, "error": str(e)}

    async def start_mining(self, threads: int = 1, chains: List[str] = ["VRSC"]) -> Dict[str, Any]:
        """
        Start mining with N threads.
        Supports multi-chain merge mining if configured.
        """
        try:
            # Note: In a production PBaaS setup, we might iterate through chains
            # or call a merge-mining specific method. For now, we set the primary.
            await self.rpc.set_generate(True, threads)
            return {"success": True, "mode": "mining", "threads": threads, "chains": chains}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def start_staking(self) -> Dict[str, Any]:
        """Start staking (setgenerate true 0)."""
        try:
            await self.rpc.set_generate(True, 0)
            return {"success": True, "mode": "staking"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_mining(self) -> Dict[str, Any]:
        """Stop all mining and staking."""
        try:
            await self.rpc.set_generate(False)
            return {"success": True, "mode": "stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── DeFi Information ──────────────────────────────────────────────────

    async def get_currencies(self) -> List[Dict[str, Any]]:
        """Returns info about known currencies."""
        known = ["VRSC", "vETH", "Bridge.vETH", "DAI.vETH", "MKR.vETH"]
        results = []
        for name in known:
            try:
                info = await self.rpc.get_currency(name)
                if info:
                    results.append({
                        "name": info.get("name", name),
                        "currencyid": info.get("currencyid", ""),
                        "supply": info.get("bestcurrencystate", {}).get("supply", 0),
                        "reservecurrencies": info.get("bestcurrencystate", {}).get("reservecurrencies", []),
                        "options": info.get("options", 0),
                    })
            except Exception:
                continue
        return results

    async def get_conversion_estimate(self, amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Estimates a currency conversion amount (read-only)."""
        try:
            # Use getcurrencyconverters to find the right AMM
            converters = await self.rpc.get_currency_converters([from_currency, to_currency])
            if converters:
                return {
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "amount": amount,
                    "estimated_return": amount * 0.995,  # Mocked 0.5% AMM slippage/fee
                    "estimated": True,
                    "converters": len(converters),
                    "note": "Exact rate determined at block inclusion time (MEV-resistant)",
                }
            return {"error": "No converters found for this pair"}
        except Exception as e:
            return {"error": str(e)}

    # ── Ethereum Bridge ───────────────────────────────────────────────────

    async def bridge_to_eth(self, amount: float, currency: str, eth_address: str) -> Dict[str, Any]:
        """Bridges currency from Verus to Ethereum via the Verus-Ethereum bridge."""
        try:
            output = {
                "address": eth_address,
                "amount": amount,
                "currency": currency,
                "exportto": "veth",
                "via": "Bridge.vETH",
            }
            txid = await self.rpc.send_currency("*", [output])
            return {"success": True, "txid": txid, "estimated_time": "30-60 minutes"}
        except Exception as e:
            logger.error(f"[Wallet] bridge to ETH: {e}")
            return {"success": False, "error": str(e)}

    async def get_bridge_status(self) -> Dict[str, Any]:
        """Returns status of the Verus-Ethereum bridge."""
        try:
            bridge = await self.rpc.get_currency("Bridge.vETH")
            pending = await self.rpc.get_pending_transfers("vETH")
            return {
                "active": bridge is not None,
                "reserves": bridge.get("bestcurrencystate", {}).get("reservecurrencies", []) if bridge else [],
                "pending_transfers": len(pending) if pending else 0,
            }
        except Exception as e:
            return {"active": False, "error": str(e)}

    # ── Identity Operations ───────────────────────────────────────────────

    async def get_identity_info(self) -> Dict[str, Any]:
        """Returns the agent's VerusID information."""
        if not self.identity:
            return {"error": "No VerusID configured"}
        try:
            data = await self.rpc.get_identity(self.identity)
            return data
        except Exception as e:
            return {"error": str(e)}

    async def update_identity_data(self, key: str, value: Any) -> Dict[str, Any]:
        """Updates VDXF data on the agent's VerusID via contentmultimap."""
        if not self.identity:
            return {"error": "No VerusID configured"}
        try:
            txid = await self.rpc.update_identity({
                "name": self.identity,
                "contentmultimap": {key: [value]}
            })
            return {"success": True, "txid": txid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _format_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes a raw RPC transaction into a clean format."""
        ts = tx.get("time") or tx.get("blocktime") or tx.get("timereceived")
        return {
            "txid": tx.get("txid", ""),
            "category": tx.get("category", "unknown"),  # send, receive, generate, immature
            "amount": tx.get("amount", 0),
            "currency": tx.get("currency", "VRSC"),
            "address": tx.get("address", ""),
            "confirmations": tx.get("confirmations", 0),
            "time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None,
            "fee": tx.get("fee", 0),
            "blockhash": tx.get("blockhash", ""),
            "comment": tx.get("comment", ""),
        }


# Singleton instance
wallet_service = VerusWalletService()
