"""
Exec Approval System for the Polytope Sovereign OS.

Replaces the content-length-only whitelist with an interactive
approval flow pushed via WebSocket:
  - exec.approval event → user sees Deny / Allow Once / Allow Always
  - Persistent allow/deny policies stored in DB

Reference: Sovereign Spec Section 5.6
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlmodel import Session, select

logger = logging.getLogger("ExecApproval")


class ExecApprovalManager:
    """
    Manages execution approval requests pushed to connected admin clients.
    """

    def __init__(self, db_engine, ws_gateway=None):
        self.db_engine = db_engine
        self.ws_gateway = ws_gateway
        self._pending: Dict[str, asyncio.Future] = {}

    async def request_approval(
        self,
        command: str,
        tool_name: str = "shell",
        context: str = "",
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """
        Request execution approval from connected admin clients.

        Returns: {"approved": bool, "persist": bool, "policy": "allow_once"|"allow_always"|"deny"}
        """
        # Check persistent policies first
        policy = self._check_policy(command, tool_name)
        if policy:
            logger.info(f"[ExecApproval] Auto-{policy} via persistent policy: {tool_name}")
            return {"approved": policy == "allow", "persist": True, "policy": policy}

        request_id = str(uuid.uuid4())[:8]

        # Push event to connected clients
        if self.ws_gateway:
            await self.ws_gateway.broadcast_event("exec.approval", {
                "request_id": request_id,
                "tool_name": tool_name,
                "command": command,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            # No gateway — auto-deny
            return {"approved": False, "persist": False, "policy": "deny"}

        # Wait for response
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"[ExecApproval] Timeout for request {request_id}")
            return {"approved": False, "persist": False, "policy": "timeout"}
        finally:
            self._pending.pop(request_id, None)

    def handle_allow(self, request_id: str, persist: bool = False,
                     command: str = "", tool_name: str = "") -> Dict[str, Any]:
        """Handle an 'Allow' response from the admin UI."""
        future = self._pending.get(request_id)
        if not future or future.done():
            return {"status": "expired"}

        result = {"approved": True, "persist": persist, "policy": "allow_always" if persist else "allow_once"}
        future.set_result(result)

        if persist and command:
            self._store_policy(command, tool_name, "allow")

        return {"status": "allowed", "persist": persist}

    def handle_deny(self, request_id: str, persist: bool = False,
                    command: str = "", tool_name: str = "") -> Dict[str, Any]:
        """Handle a 'Deny' response from the admin UI."""
        future = self._pending.get(request_id)
        if not future or future.done():
            return {"status": "expired"}

        result = {"approved": False, "persist": persist, "policy": "deny"}
        future.set_result(result)

        if persist and command:
            self._store_policy(command, tool_name, "deny")

        return {"status": "denied", "persist": persist}

    # ── Policy Storage ────────────────────────────────────────────────────

    def _check_policy(self, command: str, tool_name: str) -> Optional[str]:
        """Check if a persistent policy exists for this command/tool."""
        from .models import ExecPolicy

        with Session(self.db_engine) as session:
            # Check exact command match first
            stmt = select(ExecPolicy).where(
                ExecPolicy.tool_name == tool_name,
                ExecPolicy.command_pattern == command,
            )
            policy = session.exec(stmt).first()
            if policy:
                return policy.decision

            # Check wildcard tool-level policy
            stmt = select(ExecPolicy).where(
                ExecPolicy.tool_name == tool_name,
                ExecPolicy.command_pattern == "*",
            )
            policy = session.exec(stmt).first()
            if policy:
                return policy.decision

        return None

    def _store_policy(self, command: str, tool_name: str, decision: str):
        """Store a persistent allow/deny policy."""
        from .models import ExecPolicy

        with Session(self.db_engine) as session:
            # Upsert: check if exists
            stmt = select(ExecPolicy).where(
                ExecPolicy.tool_name == tool_name,
                ExecPolicy.command_pattern == command,
            )
            existing = session.exec(stmt).first()
            if existing:
                existing.decision = decision
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
            else:
                policy = ExecPolicy(
                    tool_name=tool_name,
                    command_pattern=command,
                    decision=decision,
                )
                session.add(policy)
            session.commit()

    def list_policies(self) -> list:
        """List all persistent exec policies."""
        from .models import ExecPolicy

        with Session(self.db_engine) as session:
            policies = session.exec(select(ExecPolicy)).all()
            return [
                {
                    "id": p.id,
                    "tool_name": p.tool_name,
                    "command_pattern": p.command_pattern,
                    "decision": p.decision,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in policies
            ]

    def delete_policy(self, policy_id: int) -> bool:
        """Delete a persistent exec policy."""
        from .models import ExecPolicy

        with Session(self.db_engine) as session:
            policy = session.get(ExecPolicy, policy_id)
            if not policy:
                return False
            session.delete(policy)
            session.commit()
            return True
