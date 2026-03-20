"""
Upgraded HeartbeatDaemon — Structured Multi-Path Orders
========================================================

Replaces the single-path text-parsing heartbeat with a structured,
multi-action, per-agent-capable heartbeat system.

Key improvements over the original:
  1. Orders are structured JSON objects with typed probe_type and action_type
  2. Five action paths: notify_ws, notify_bridge, execute_objective,
     evaluate_goal, log_only, pcl_signal
  3. Per-order interval control (not a global 15-minute gate)
  4. Backward compatible: legacy "- [x] text" markdown orders are auto-migrated
  5. Per-agent orders loaded from AgentRecord.heartbeat_orders
  6. Outcomes persisted to HeartbeatOrderRecord for UI display and cooldown
  7. pcl_signal actions feed directly into H-LSM for PCL consumption
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlmodel import Session, select, col

from .logging_config import get_logger
from .models import AgentRecord, HeartbeatOrderRecord

logger = get_logger("Heartbeat")

# ─── Default Interval ─────────────────────────────────────────────────────────
DEFAULT_INTERVAL_MINUTES: int = 15
TICK_SECONDS: float = 60.0   # Check every minute whether any order is due


# ─── Order Dataclass ──────────────────────────────────────────────────────────

def _make_order_id() -> str:
    return str(uuid.uuid4())[:8]


def parse_legacy_heartbeat_string(raw: str) -> List[Dict]:
    """
    Migrate legacy HEARTBEAT.md / Soul Manifest heartbeat string to structured orders.
    Every "- [x] text" line becomes a execute_objective order with the text as label.
    Every "- [ ] text" line is skipped (inactive).
    """
    orders = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [x]"):
            label = stripped.replace("- [x]", "").strip()
            if label:
                orders.append({
                    "id": hashlib.sha256(label.encode()).hexdigest()[:8],
                    "label": label,
                    "active": True,
                    "probe_type": "task_deadline",
                    "probe_config": {"path": "TASKS.md"},
                    "action_type": "execute_objective",
                    "action_config": {"objective_template": label},
                    "interval_minutes": DEFAULT_INTERVAL_MINUTES,
                })
    return orders


def load_orders_from_manifest(manifest_data: Optional[Dict]) -> List[Dict]:
    """
    Load heartbeat orders from a Soul Manifest dict.
    Handles both new structured JSON array and legacy markdown string.
    """
    if not manifest_data:
        return []
    heartbeat = manifest_data.get("heartbeat", "")
    if not heartbeat:
        return []
    if isinstance(heartbeat, list):
        return heartbeat
    if isinstance(heartbeat, str):
        # Try JSON first
        stripped = heartbeat.strip()
        if stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        # Fall back to legacy markdown parsing
        return parse_legacy_heartbeat_string(heartbeat)
    return []


# ─── Probe Implementations ────────────────────────────────────────────────────

async def run_probe(probe_type: str, probe_config: Dict, agent_id: Optional[str]) -> Tuple[bool, str]:
    """
    Run a probe and return (did_fire: bool, detail: str).
    did_fire=True means the condition was detected and action should run.
    did_fire=False means no change / condition not met.
    """
    try:
        if probe_type == "file_watch":
            return await _probe_file_watch(probe_config)

        elif probe_type == "task_deadline":
            return await _probe_task_deadline(probe_config)

        elif probe_type == "goal_progress":
            return await _probe_goal_progress(probe_config)

        elif probe_type == "url_fetch":
            return await _probe_url_fetch(probe_config)

        elif probe_type == "memory_pattern":
            return await _probe_memory_pattern(probe_config)

        elif probe_type == "system_health":
            return await _probe_system_health(probe_config)

        elif probe_type == "bridge_silence":
            return await _probe_bridge_silence(probe_config)

        elif probe_type == "cron_expression":
            # Cron probes always fire — they are schedule-driven not condition-driven
            return True, "cron_expression: scheduled"

        else:
            logger.warning(f"[HB] Unknown probe_type: {probe_type}")
            return False, f"Unknown probe_type: {probe_type}"

    except Exception as e:
        logger.error(f"[HB] Probe {probe_type} error: {e}", exc_info=True)
        return False, f"Probe error: {e}"


async def _probe_file_watch(config: Dict) -> Tuple[bool, str]:
    """Watch a file or directory for changes using SHA256 hashing."""
    path = config.get("path", "")
    state_key = f"file_watch:{path}"

    if not os.path.exists(path):
        return False, f"Path not found: {path}"

    try:
        if os.path.isfile(path):
            with open(path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
        else:
            # Directory: hash all file mtimes
            entries = sorted(
                (os.path.join(r, f) for r, _, fs in os.walk(path) for f in fs)
            )
            combined = "".join(
                f"{p}:{os.path.getmtime(p)}" for p in entries if os.path.exists(p)
            )
            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        # Load last known hash from simple state file
        state_path = f".hb_state_{hashlib.sha256(path.encode()).hexdigest()[:8]}.json"
        last_hash = ""
        if os.path.exists(state_path):
            try:
                with open(state_path) as f:
                    last_hash = json.load(f).get("hash", "")
            except Exception:
                pass

        if current_hash != last_hash:
            with open(state_path, "w") as f:
                json.dump({"hash": current_hash, "ts": time.time()}, f)
            return True, f"File changed: {path}"

        return False, "No change detected"
    except Exception as e:
        return False, f"File watch error: {e}"


async def _probe_task_deadline(config: Dict) -> Tuple[bool, str]:
    """Parse TASKS.md for unchecked items with past due dates."""
    path = config.get("path", "TASKS.md")
    threshold_days = int(config.get("threshold_days", 0))

    if not os.path.exists(path):
        return False, f"Tasks file not found: {path}"

    today = datetime.now(timezone.utc).date()
    expired = []
    try:
        with open(path, "r") as f:
            for line in f:
                if "- [ ]" in line:
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", line)
                    if m:
                        try:
                            due = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                            overdue_days = (today - due).days
                            if overdue_days >= threshold_days:
                                expired.append(f"{line.strip()} (overdue {overdue_days}d)")
                        except ValueError:
                            pass
        if expired:
            return True, f"{len(expired)} overdue tasks: {'; '.join(expired[:3])}"
        return False, "No overdue tasks"
    except Exception as e:
        return False, f"Task deadline probe error: {e}"


async def _probe_goal_progress(config: Dict) -> Tuple[bool, str]:
    """Check whether a goal's progress is below a threshold."""
    from . import services
    goal_id = config.get("goal_id")
    threshold = float(config.get("threshold_pct", 50.0))

    if not goal_id or not services.goal_engine:
        return False, "Goal ID or engine not available"

    try:
        goal = await services.goal_engine.get_goal(int(goal_id))
        if not goal:
            return False, f"Goal {goal_id} not found"

        progress = (goal.metric_current / max(goal.metric_target or 100, 1)) * 100
        if progress < threshold:
            return True, (
                f"Goal '{goal.title}' at {progress:.1f}% "
                f"(below threshold {threshold:.0f}%)"
            )
        return False, f"Goal '{goal.title}' at {progress:.1f}% — above threshold"
    except Exception as e:
        return False, f"Goal probe error: {e}"


async def _probe_url_fetch(config: Dict) -> Tuple[bool, str]:
    """Fetch a URL and check for a keyword or content change."""
    url = config.get("url", "")
    keyword = config.get("keyword", "")
    check_change = config.get("check_change", False)

    if not url:
        return False, "No URL configured"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "AlluciHeartbeat/1.0"})
            resp.raise_for_status()
            body = resp.text[:5000]  # Limit to first 5000 chars

        if keyword:
            if keyword.lower() in body.lower():
                return True, f"Keyword '{keyword}' found at {url}"
            return False, f"Keyword '{keyword}' not found at {url}"

        if check_change:
            state_key = hashlib.sha256(url.encode()).hexdigest()[:8]
            state_path = f".hb_url_{state_key}.json"
            current_hash = hashlib.sha256(body.encode()).hexdigest()
            last_hash = ""
            if os.path.exists(state_path):
                try:
                    with open(state_path) as f:
                        last_hash = json.load(f).get("hash", "")
                except Exception:
                    pass

            if current_hash != last_hash:
                with open(state_path, "w") as f:
                    json.dump({"hash": current_hash, "ts": time.time()}, f)
                return True, f"Content changed at {url}"
            return False, f"No change at {url}"

        # Default: just confirm URL is reachable
        return True, f"URL reachable: {url} ({resp.status_code})"

    except httpx.HTTPError as e:
        return False, f"URL fetch failed: {e}"


async def _probe_memory_pattern(config: Dict) -> Tuple[bool, str]:
    """Check H-LSM L1 for a recurring topic or unresolved pattern."""
    from . import services
    query = config.get("query", "")
    min_occurrences = int(config.get("min_occurrences", 2))

    if not query or not services.hlsm_manager:
        return False, "No query or H-LSM not available"

    try:
        results = await services.hlsm_manager.l1_search(query, limit=20)
        if len(results) >= min_occurrences:
            return True, (
                f"Pattern '{query}' found {len(results)} times in episodic memory"
            )
        return False, f"Pattern '{query}' found {len(results)} times (below {min_occurrences})"
    except Exception as e:
        return False, f"Memory pattern probe error: {e}"


async def _probe_system_health(config: Dict) -> Tuple[bool, str]:
    """Check task failure rate in the past N hours."""
    from . import services
    from .models import TaskRecord
    from sqlalchemy import text as sa_text
    from .database import engine as db_engine

    failure_threshold = int(config.get("failure_threshold", 3))
    hours = float(config.get("hours", 4.0))
    cutoff = time.time() - (hours * 3600)

    try:
        with Session(db_engine) as session:
            from datetime import datetime, timezone
            records = session.exec(
                select(TaskRecord).where(TaskRecord.status == "failed")
                .order_by(col(TaskRecord.end_time).desc())
                .limit(100)
            ).all()

        recent_failures = [
            r for r in records
            if r.end_time and r.end_time.timestamp() > cutoff
        ]
        if len(recent_failures) >= failure_threshold:
            actions = [r.action for r in recent_failures]
            return True, (
                f"{len(recent_failures)} failures in last {hours:.0f}h: "
                f"{', '.join(actions[:3])}"
            )
        return False, f"{len(recent_failures)} failures in last {hours:.0f}h (below {failure_threshold})"
    except Exception as e:
        return False, f"System health probe error: {e}"


async def _probe_bridge_silence(config: Dict) -> Tuple[bool, str]:
    """Check a specific bridge for unanswered messages."""
    from . import services
    bridge_id = config.get("bridge_id", "")
    silence_hours = float(config.get("silence_hours", 4.0))

    if not bridge_id:
        return False, "No bridge_id configured"

    adapter = services.channel_registry.get(bridge_id) if services.channel_registry else None
    if not adapter:
        return False, f"Bridge '{bridge_id}' not found in registry"

    last_inbound = getattr(adapter, "last_inbound_at", None)
    last_outbound = getattr(adapter, "last_outbound_at", None)

    if last_inbound and (last_outbound is None or last_inbound > last_outbound):
        hours_silent = (time.time() - last_inbound) / 3600
        if hours_silent >= silence_hours:
            sender = getattr(adapter, "last_inbound_sender", "unknown")
            return True, (
                f"Bridge '{bridge_id}' has unanswered message from {sender} "
                f"for {hours_silent:.1f}h"
            )
    return False, f"Bridge '{bridge_id}' has no unanswered messages"


# ─── Action Implementations ───────────────────────────────────────────────────

async def run_action(
    action_type: str,
    action_config: Dict,
    probe_detail: str,
    order: Dict,
    agent_id: Optional[str],
    orchestrator=None,
    ws_gateway=None,
    hlsm_manager=None,
) -> Tuple[str, str]:
    """
    Execute the action for a fired order.
    Returns (outcome: str, detail: str).
    outcome is one of: "success" | "failed" | "skipped"
    """
    try:
        if action_type == "notify_ws":
            return await _action_notify_ws(action_config, probe_detail, order, ws_gateway)

        elif action_type == "notify_bridge":
            return await _action_notify_bridge(action_config, probe_detail, order, orchestrator)

        elif action_type == "execute_objective":
            return await _action_execute_objective(action_config, probe_detail, order, agent_id, orchestrator)

        elif action_type == "evaluate_goal":
            return await _action_evaluate_goal(action_config)

        elif action_type == "log_only":
            return await _action_log_only(probe_detail, order, hlsm_manager)

        elif action_type == "pcl_signal":
            return await _action_pcl_signal(action_config, probe_detail, order, agent_id, hlsm_manager)

        else:
            logger.warning(f"[HB] Unknown action_type: {action_type}")
            return "skipped", f"Unknown action_type: {action_type}"

    except Exception as e:
        logger.error(f"[HB] Action {action_type} error: {e}", exc_info=True)
        return "failed", str(e)


async def _action_notify_ws(config: Dict, probe_detail: str, order: Dict, ws_gateway) -> Tuple[str, str]:
    """Push a notification to the WebSocket (UI notification)."""
    if not ws_gateway:
        return "skipped", "No WebSocket gateway available"

    message = config.get("message_template", order.get("label", "Heartbeat alert"))
    message = message.replace("{probe_detail}", probe_detail)

    await ws_gateway.broadcast_event("heartbeat.notification", {
        "order_id": order.get("id"),
        "label": order.get("label"),
        "message": message,
        "probe_detail": probe_detail,
        "timestamp": time.time(),
    })
    return "success", f"WebSocket notification sent: {message[:80]}"


async def _action_notify_bridge(config: Dict, probe_detail: str, order: Dict, orchestrator) -> Tuple[str, str]:
    """Send a message via a specific bridge channel."""
    bridge_id = config.get("bridge_id", "")
    recipient = config.get("recipient", "")
    message_template = config.get("message_template", "{label}: {probe_detail}")

    message = (
        message_template
        .replace("{label}", order.get("label", ""))
        .replace("{probe_detail}", probe_detail)
    )

    if not orchestrator or not bridge_id:
        return "skipped", "No orchestrator or bridge_id"

    # Route via orchestrator's inbound handler using bridge dispatch
    from . import services
    adapter = services.channel_registry.get(bridge_id) if services.channel_registry else None
    if not adapter:
        return "failed", f"Bridge '{bridge_id}' not found"

    result = await adapter.send_message(recipient=recipient, content=message)
    if result.get("status") == "success":
        return "success", f"Sent via {bridge_id} to {recipient}"
    return "failed", str(result)


async def _action_execute_objective(
    config: Dict, probe_detail: str, order: Dict,
    agent_id: Optional[str], orchestrator
) -> Tuple[str, str]:
    """Execute a DAG objective via the orchestrator."""
    if not orchestrator:
        return "skipped", "No orchestrator available"

    template = config.get(
        "objective_template",
        f"[Heartbeat: {order.get('label', 'Order')}] {probe_detail}"
    )
    objective = template.replace("{probe_detail}", probe_detail)
    autonomy = config.get("autonomy", "RESTRICTED")

    # Inject agent context if this is a per-agent order
    if agent_id:
        objective = f"[Agent: {agent_id}] {objective}"

    result = await orchestrator.execute_objective(objective=objective, autonomy=autonomy)
    status = result.get("status", "unknown") if isinstance(result, dict) else str(result)
    return (
        "success" if "fail" not in status.lower() else "failed",
        f"Executed: {objective[:100]} → {status}"
    )


async def _action_evaluate_goal(config: Dict) -> Tuple[str, str]:
    """Trigger GoalsEngine.evaluate_progress() for a specific goal."""
    from . import services
    goal_id = config.get("goal_id")
    if not goal_id:
        return "skipped", "No goal_id in action_config"

    result = await services.goal_engine.evaluate_progress(int(goal_id))
    return "success", f"Goal {goal_id} progress evaluated: {result}"


async def _action_log_only(probe_detail: str, order: Dict, hlsm_manager) -> Tuple[str, str]:
    """Write the probe result to H-LSM L1 with no user-facing action."""
    if not hlsm_manager:
        return "skipped", "H-LSM not available"

    content = f"[Heartbeat Log] {order.get('label', '')}: {probe_detail}"
    await hlsm_manager.l1_store(
        content=content,
        source="heartbeat_log",
        topological_importance=0.8,
    )
    return "success", f"Logged to H-LSM: {content[:80]}"


async def _action_pcl_signal(
    config: Dict, probe_detail: str, order: Dict,
    agent_id: Optional[str], hlsm_manager
) -> Tuple[str, str]:
    """
    Store a structured PCL signal to H-LSM L1.
    The PCL's next cycle will read this via _observe_memory()
    and the HeartbeatSignalDetector will surface it as an Opportunity.
    """
    if not hlsm_manager:
        return "skipped", "H-LSM not available"

    signal_label = config.get("signal_label", order.get("label", "heartbeat_signal"))
    priority = config.get("priority", 3)
    agent_tag = f"[Agent:{agent_id}] " if agent_id else ""

    content = (
        f"[PCL_SIGNAL] {agent_tag}{signal_label}: {probe_detail} "
        f"(priority={priority}, order_id={order.get('id', '?')})"
    )

    await hlsm_manager.l1_store(
        content=content,
        source="heartbeat_signal",
        topological_importance=1.0 + (1 - (priority / 5)),  # P1=1.8, P5=0.8
    )

    logger.info(f"[HB] PCL signal stored: {content[:100]}")
    return "success", f"PCL signal stored: {signal_label}"


# ─── HeartbeatDaemon ──────────────────────────────────────────────────────────

class HeartbeatDaemon:
    """
    Upgraded Heartbeat Daemon with structured multi-path orders.

    Loads orders from:
      1. Soul Manifest (root agent) — supports JSON array and legacy markdown
      2. AgentRecord.heartbeat_orders — per-agent structured orders

    Each order has its own probe_type, action_type, and interval_minutes.
    Outcomes are persisted to HeartbeatOrderRecord for UI display.

    Runs on a 60-second tick loop that checks which orders are due.
    """

    def __init__(
        self,
        orchestrator,
        vault,
        db_engine,
        interval_seconds: int = 900,
        quiet_start: int = 22,
        quiet_end: int = 7,
    ):
        self.orchestrator = orchestrator
        self.vault = vault
        self.db_engine = db_engine
        self.default_interval = interval_seconds // 60  # convert to minutes
        self.quiet_start = quiet_start
        self.quiet_end = quiet_end
        self.ws_gateway = None
        self._hlsm = None           # Injected after services init
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = get_logger("Heartbeat")

    def inject_hlsm(self, hlsm) -> None:
        """Inject H-LSM manager after services initialization."""
        self._hlsm = hlsm

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        self.logger.info("[HB] Heartbeat Daemon started (structured orders mode)")
        self._task = asyncio.create_task(self._tick_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("[HB] Heartbeat Daemon stopped")

    async def _tick_loop(self) -> None:
        """Tick every 60 seconds, evaluate which orders are due."""
        while self._running:
            try:
                await self._evaluate_all_orders()
            except Exception as e:
                self.logger.error(f"[HB] Tick error: {e}", exc_info=True)
            try:
                await asyncio.sleep(TICK_SECONDS)
            except asyncio.CancelledError:
                break

    # ─── Quiet Hours ──────────────────────────────────────────────────────────

    def _is_quiet_hours(self) -> bool:
        now = datetime.now(timezone.utc).hour
        if self.quiet_start > self.quiet_end:
            return now >= self.quiet_start or now < self.quiet_end
        return self.quiet_start <= now < self.quiet_end

    # ─── Load Orders ──────────────────────────────────────────────────────────

    async def _load_root_orders(self) -> List[Dict]:
        """Load structured orders from the root Soul Manifest."""
        try:
            if self.vault:
                manifest_data = await self.vault.retrieve_secret("soul_manifest")
                return load_orders_from_manifest(manifest_data)
        except Exception as e:
            self.logger.error(f"[HB] Failed to load root orders: {e}")
        return []

    def _load_agent_orders(self) -> List[Tuple[str, Dict]]:
        """
        Load heartbeat orders from all ACTIVE AgentRecord entries.
        Returns list of (agent_id, order_dict) tuples.
        """
        result = []
        try:
            with Session(self.db_engine) as session:
                agents = session.exec(
                    select(AgentRecord).where(AgentRecord.status == "ACTIVE")
                ).all()

            for agent in agents:
                if not agent.heartbeat_orders:
                    continue
                try:
                    orders = json.loads(agent.heartbeat_orders)
                    for order in orders:
                        if isinstance(order, dict) and order.get("active", False):
                            result.append((agent.id, order))
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"[HB] Agent {agent.id} has invalid heartbeat_orders JSON: {e}"
                    )
        except Exception as e:
            self.logger.error(f"[HB] Failed to load agent orders: {e}", exc_info=True)
        return result

    # ─── Due Check ────────────────────────────────────────────────────────────

    def _is_order_due(self, order: Dict, agent_id: Optional[str]) -> bool:
        """
        Check whether an order is due based on its interval and last-fired time.
        """
        interval_minutes = int(order.get("interval_minutes", self.default_interval))
        interval_seconds = interval_minutes * 60
        order_id = order.get("id", "")

        try:
            with Session(self.db_engine) as session:
                last = session.exec(
                    select(HeartbeatOrderRecord)
                    .where(
                        HeartbeatOrderRecord.order_id == order_id,
                        HeartbeatOrderRecord.agent_id == agent_id,
                    )
                    .order_by(col(HeartbeatOrderRecord.fired_at).desc())
                    .limit(1)
                ).first()

            if last is None:
                return True  # Never fired — fire now

            elapsed = time.time() - last.fired_at
            return elapsed >= interval_seconds

        except Exception as e:
            self.logger.debug(f"[HB] Due check error for order {order_id}: {e}")
            return True  # Default to fire on error

    # ─── Run One Order ────────────────────────────────────────────────────────

    async def _run_order(self, order: Dict, agent_id: Optional[str]) -> None:
        """
        Run a single heartbeat order: probe → action → persist outcome.
        """
        order_id = order.get("id", "?")
        label = order.get("label", "Unnamed Order")
        probe_type = order.get("probe_type", "task_deadline")
        probe_config = order.get("probe_config", {})
        action_type = order.get("action_type", "log_only")
        action_config = order.get("action_config", {})

        agent_tag = f"[Agent:{agent_id}] " if agent_id else "[Root] "
        self.logger.info(f"[HB] {agent_tag}Running order '{label}' ({probe_type} → {action_type})")

        # Run probe
        fired, probe_detail = await run_probe(probe_type, probe_config, agent_id)

        if not fired:
            # Log no-change at debug level, persist as no_change
            self.logger.debug(f"[HB] {agent_tag}Order '{label}': no change — {probe_detail}")
            self._persist_outcome(order_id, agent_id, probe_type, action_type, "no_change", probe_detail)
            return

        self.logger.info(f"[HB] {agent_tag}Order '{label}' FIRED: {probe_detail}")

        # Quiet hours: suppress notify actions, allow execute and signal
        if self._is_quiet_hours() and action_type in ("notify_ws", "notify_bridge"):
            self.logger.info(f"[HB] {agent_tag}Quiet hours — suppressing notification for '{label}'")
            self._persist_outcome(order_id, agent_id, probe_type, action_type, "skipped", "quiet_hours")
            return

        # Run action
        outcome, detail = await run_action(
            action_type=action_type,
            action_config=action_config,
            probe_detail=probe_detail,
            order=order,
            agent_id=agent_id,
            orchestrator=self.orchestrator,
            ws_gateway=self.ws_gateway,
            hlsm_manager=self._hlsm,
        )

        # Persist outcome
        signal_stored = (action_type == "pcl_signal" and outcome == "success")
        self._persist_outcome(
            order_id, agent_id, probe_type, action_type, outcome, detail, signal_stored
        )
        self.logger.info(f"[HB] {agent_tag}Order '{label}': {outcome} — {detail[:100]}")

    def _persist_outcome(
        self, order_id: str, agent_id: Optional[str],
        probe_type: str, action_type: str,
        outcome: str, detail: str, signal_stored: bool = False
    ) -> None:
        record = HeartbeatOrderRecord(
            order_id=order_id,
            agent_id=agent_id,
            fired_at=time.time(),
            probe_type=probe_type,
            action_type=action_type,
            outcome=outcome,
            detail=detail[:500] if detail else None,
            signal_stored=signal_stored,
        )
        try:
            with Session(self.db_engine) as session:
                session.add(record)
                session.commit()
        except Exception as e:
            self.logger.error(f"[HB] Failed to persist outcome: {e}")

    # ─── Main Evaluation Loop ─────────────────────────────────────────────────

    async def _evaluate_all_orders(self) -> None:
        """
        Load all orders (root + per-agent), check which are due, run them.
        """
        # Broadcast alive heartbeat
        if self.ws_gateway:
            asyncio.create_task(self.ws_gateway.broadcast_event("system.heartbeat", {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "NOMINAL",
            }))

        # Load root orders
        root_orders = await self._load_root_orders()
        active_root = [(None, o) for o in root_orders if o.get("active", False)]

        # Load agent orders
        agent_orders = self._load_agent_orders()

        all_orders = active_root + agent_orders

        if not all_orders:
            self.logger.debug("[HB] No active orders")
            return

        # Check which are due and run them
        due_orders = [
            (agent_id, order)
            for agent_id, order in all_orders
            if self._is_order_due(order, agent_id)
        ]

        if not due_orders:
            self.logger.debug(f"[HB] {len(all_orders)} orders loaded, none due yet")
            return

        self.logger.info(f"[HB] {len(due_orders)}/{len(all_orders)} orders due")

        # Run due orders concurrently (max 5 at once to avoid flooding)
        semaphore = asyncio.Semaphore(5)

        async def run_with_semaphore(agent_id, order):
            async with semaphore:
                await self._run_order(order, agent_id)

        await asyncio.gather(*[
            run_with_semaphore(agent_id, order)
            for agent_id, order in due_orders
        ], return_exceptions=True)

    # ─── UI Introspection ─────────────────────────────────────────────────────

    def get_order_history(self, order_id: str, agent_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Returns recent execution history for an order. Used by the UI editor."""
        try:
            with Session(self.db_engine) as session:
                records = session.exec(
                    select(HeartbeatOrderRecord)
                    .where(
                        HeartbeatOrderRecord.order_id == order_id,
                        HeartbeatOrderRecord.agent_id == agent_id,
                    )
                    .order_by(col(HeartbeatOrderRecord.fired_at).desc())
                    .limit(limit)
                ).all()
            return [
                {
                    "fired_at": r.fired_at,
                    "outcome": r.outcome,
                    "detail": r.detail,
                    "signal_stored": r.signal_stored,
                }
                for r in records
            ]
        except Exception as e:
            self.logger.error(f"[HB] get_order_history error: {e}")
            return []
