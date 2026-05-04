"""
HeartbeatDaemon — Upgraded to six independent action paths.

Every heartbeat order is a structured JSON object with:
  probe_type   — what condition to check
  action_type  — what to do when it fires

Six action paths:
  notify_ws         Push WebSocket notification to the UI
  notify_bridge     Send a message via a named bridge channel
  execute_objective Run a DAG objective via the orchestrator
  evaluate_goal     Call GoalsEngine.evaluate_progress()
  log_only          Write to H-LSM memory with no user-visible output
  pcl_signal        Store a structured signal for PCL HeartbeatSignalDetector

Eight probe types:
  file_watch        SHA-256 hash change on a file or directory
  task_deadline     Unchecked items with past due dates in a markdown file
  goal_progress     Goal metric_current below a percentage threshold
  url_fetch         Keyword match or content change at a URL
  memory_pattern    Topic appearing >= N times in H-LSM L1 episodic memory
  system_health     Task failure count in the past N hours
  bridge_silence    Bridge channel with unanswered inbound message
  cron_expression   Schedule-driven: always fires when the interval elapses

Backward-compatible:
  - Constructor signature unchanged: HeartbeatDaemon(orchestrator, vault[, interval_seconds])
  - Legacy "- [x] text" markdown heartbeat strings auto-migrate to
    {probe_type: task_deadline, action_type: execute_objective} orders
  - Per-agent orders loaded from AgentRecord.heartbeat_orders in the DB

PCL integration:
  pcl_signal orders store entries to H-LSM with source="heartbeat_signal".
  PCL's HeartbeatSignalDetector picks them up on the next cycle.
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
from .ace.affect_kernel import AffectiveState
from .engine.dream_cycle import SleepStateOrchestrator

logger = get_logger("Heartbeat")

_URL_PATTERN = re.compile(r'https?://', re.IGNORECASE)
_NETWORK_CONSENT_MARKER = "[NETWORK_OK]"

def _order_requires_network(order_text: str) -> bool:
    return bool(_URL_PATTERN.search(order_text))

def _order_has_network_consent(order_text: str) -> bool:
    return _NETWORK_CONSENT_MARKER in order_text

async def execute_standing_order(order_text: str):
    """Executes a single standing order with network consent enforcement."""
    if _order_requires_network(order_text):
        if not _order_has_network_consent(order_text):
            logger.warning(f"[ HEARTBEAT ] Blocked order missing [NETWORK_OK]: {order_text[:50]}...")
            return f"Blocked: Missing {_NETWORK_CONSENT_MARKER} for network access."
    
    # Original execution logic follows...

# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_INTERVAL_MINUTES: int = 15
TICK_SECONDS: float = 60.0
MAX_CONCURRENT_ORDERS: int = 5


# ─── Order helpers ────────────────────────────────────────────────────────────

def _parse_legacy_markdown(raw: str) -> List[Dict]:
    """
    Migrate "- [x] text" markdown to structured execute_objective orders.
    Called when heartbeat field contains a string rather than a JSON array.
    """
    orders: List[Dict] = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [x]"):
            label = stripped.replace("- [x]", "").strip()
            if not label:
                continue
            orders.append(
                {
                    "id": hashlib.sha256(label.encode()).hexdigest()[:8],
                    "label": label,
                    "active": True,
                    "probe_type": "task_deadline",
                    "probe_config": {"path": "TASKS.md"},
                    "action_type": "execute_objective",
                    "action_config": {
                        "objective_template": label,
                        "autonomy": "RESTRICTED",
                    },
                    "interval_minutes": DEFAULT_INTERVAL_MINUTES,
                }
            )
    return orders


def _load_orders_from_manifest(manifest_data: Optional[Dict]) -> List[Dict]:
    """Load active orders from a Soul Manifest dict. Handles JSON and legacy markdown."""
    if not manifest_data:
        return []
    raw = manifest_data.get("heartbeat", "")
    if not raw:
        return []
    if isinstance(raw, list):
        return [o for o in raw if isinstance(o, dict)]
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [o for o in parsed if isinstance(o, dict)]
            except json.JSONDecodeError:
                pass
        return _parse_legacy_markdown(raw)
    return []


# ─── Probes ───────────────────────────────────────────────────────────────────

async def _run_probe(
    probe_type: str, probe_config: Dict, agent_id: Optional[str]
) -> Tuple[bool, str]:
    """
    Run a probe and return (did_fire, detail_string).
    did_fire=True means the condition is met and the action should run.
    All exceptions are caught and returned as did_fire=False with detail.
    """
    try:
        if probe_type == "file_watch":
            return await _probe_file_watch(probe_config)
        if probe_type == "task_deadline":
            return await _probe_task_deadline(probe_config)
        if probe_type == "goal_progress":
            return await _probe_goal_progress(probe_config)
        if probe_type == "url_fetch":
            return await _probe_url_fetch(probe_config)
        if probe_type == "memory_pattern":
            return await _probe_memory_pattern(probe_config)
        if probe_type == "system_health":
            return await _probe_system_health(probe_config)
        if probe_type == "bridge_silence":
            return await _probe_bridge_silence(probe_config)
        if probe_type == "cron_expression":
            return True, "cron_expression: scheduled fire"
        logger.warning("[HB] Unknown probe_type: %r", probe_type)
        return False, f"Unknown probe_type: {probe_type}"
    except Exception as exc:
        logger.error("[HB] Probe %s raised: %s", probe_type, exc, exc_info=True)
        return False, f"Probe error: {type(exc).__name__}: {exc}"


async def _probe_file_watch(cfg: Dict) -> Tuple[bool, str]:
    path = cfg.get("path", "")
    if not path or not os.path.exists(path):
        return False, f"Path not found: {path!r}"
    try:
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                current_hash = hashlib.sha256(fh.read()).hexdigest()
        else:
            entries = sorted(
                os.path.join(r, fn) for r, _, fs in os.walk(path) for fn in fs
            )
            blob = "".join(
                f"{p}:{os.path.getmtime(p)}" for p in entries if os.path.exists(p)
            )
            current_hash = hashlib.sha256(blob.encode()).hexdigest()

        state_key = hashlib.sha256(path.encode()).hexdigest()[:8]
        state_path = f".hb_fw_{state_key}.json"
        last_hash = ""
        if os.path.exists(state_path):
            try:
                with open(state_path) as fh:
                    last_hash = json.load(fh).get("hash", "")
            except Exception:
                pass

        if current_hash != last_hash:
            with open(state_path, "w") as fh:
                json.dump({"hash": current_hash, "ts": time.time()}, fh)
            return True, f"File changed: {path}"
        return False, "No change detected"
    except Exception as exc:
        logger.error("[HB] file_watch error: %s", exc, exc_info=True)
        return False, f"File watch error: {exc}"


async def _probe_task_deadline(cfg: Dict) -> Tuple[bool, str]:
    path = cfg.get("path", "TASKS.md")
    threshold_days = int(cfg.get("threshold_days", 0))
    if not os.path.exists(path):
        return False, f"Tasks file not found: {path!r}"

    today = datetime.now(timezone.utc).date()
    expired: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if "- [ ]" in line:
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", line)
                    if m:
                        try:
                            due = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                            if (today - due).days >= threshold_days:
                                expired.append(line.strip()[:100])
                        except ValueError:
                            pass
        if expired:
            return True, f"{len(expired)} overdue tasks: {'; '.join(expired[:3])}"
        return False, "No overdue tasks"
    except Exception as exc:
        logger.error("[HB] task_deadline error: %s", exc, exc_info=True)
        return False, f"Task deadline error: {exc}"


async def _probe_goal_progress(cfg: Dict) -> Tuple[bool, str]:
    from . import services
    goal_id = cfg.get("goal_id")
    threshold = float(cfg.get("threshold_pct", 50.0))
    if not goal_id:
        return False, "No goal_id in probe_config"
    if not getattr(services, "goal_engine", None):
        return False, "GoalsEngine not available"
    try:
        goal = await services.goal_engine.get_goal(int(goal_id))
        if not goal:
            return False, f"Goal {goal_id} not found"
        progress = (goal.metric_current / max(goal.metric_target or 100.0, 1.0)) * 100
        if progress < threshold:
            return True, (
                f"Goal '{goal.title}' at {progress:.1f}% (threshold {threshold:.0f}%)"
            )
        return False, f"Goal '{goal.title}' at {progress:.1f}% — above threshold"
    except Exception as exc:
        logger.error("[HB] goal_progress error: %s", exc, exc_info=True)
        return False, f"Goal probe error: {exc}"


async def _probe_url_fetch(cfg: Dict) -> Tuple[bool, str]:
    url = cfg.get("url", "")
    keyword = cfg.get("keyword", "")
    check_change = bool(cfg.get("check_change", False))
    if not url:
        return False, "No URL configured"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                url, headers={"User-Agent": "AlluciHeartbeat/1.0"}
            )
            resp.raise_for_status()
            body = resp.text[:8000]

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
                    with open(state_path) as fh:
                        last_hash = json.load(fh).get("hash", "")
                except Exception:
                    pass
            if current_hash != last_hash:
                with open(state_path, "w") as fh:
                    json.dump({"hash": current_hash, "ts": time.time()}, fh)
                return True, f"Content changed at {url}"
            return False, f"No change at {url}"

        return True, f"URL reachable: {url} (HTTP {resp.status_code})"
    except httpx.HTTPError as exc:
        return False, f"URL fetch failed: {exc}"
    except Exception as exc:
        logger.error("[HB] url_fetch error: %s", exc, exc_info=True)
        return False, f"URL fetch error: {exc}"


async def _probe_memory_pattern(cfg: Dict) -> Tuple[bool, str]:
    from . import services
    query = cfg.get("query", "")
    min_occ = int(cfg.get("min_occurrences", 2))
    if not query:
        return False, "No query in probe_config"
    mem = getattr(services, "hlsm_manager", None) or getattr(services, "memory", None)
    if not mem:
        return False, "Memory manager not available"
    try:
        results = await mem.search(query, limit=20)
        if len(results) >= min_occ:
            return True, f"Pattern '{query}' found {len(results)}× in episodic memory"
        return False, f"Pattern '{query}' found {len(results)}× (min={min_occ})"
    except Exception as exc:
        logger.error("[HB] memory_pattern error: %s", exc, exc_info=True)
        return False, f"Memory pattern error: {exc}"


async def _probe_system_health(cfg: Dict) -> Tuple[bool, str]:
    from .models import TaskRecord
    from .database import engine as db_engine

    failure_threshold = int(cfg.get("failure_threshold", 3))
    hours = float(cfg.get("hours", 4.0))
    cutoff_ts = time.time() - (hours * 3600)
    try:
        with Session(db_engine) as session:
            records = session.exec(
                select(TaskRecord)
                .where(TaskRecord.status == "failed")
                .order_by(col(TaskRecord.end_time).desc())
                .limit(100)
            ).all()
        recent = [
            r.action
            for r in records
            if r.end_time and r.end_time.timestamp() > cutoff_ts
        ]
        if len(recent) >= failure_threshold:
            return True, (
                f"{len(recent)} failures in last {hours:.0f}h: "
                f"{', '.join(recent[:3])}"
            )
        return False, f"{len(recent)} failures in last {hours:.0f}h (below {failure_threshold})"
    except Exception as exc:
        logger.error("[HB] system_health error: %s", exc, exc_info=True)
        return False, f"System health error: {exc}"


async def _probe_bridge_silence(cfg: Dict) -> Tuple[bool, str]:
    from . import services

    bridge_id = cfg.get("bridge_id", "")
    silence_hours = float(cfg.get("silence_hours", 4.0))
    if not bridge_id:
        return False, "No bridge_id in probe_config"
    adapter = services.channel_registry.get(bridge_id) if services.channel_registry else None
    if not adapter:
        return False, f"Bridge '{bridge_id}' not in registry"

    last_inbound = getattr(adapter, "last_inbound_at", None)
    last_outbound = getattr(adapter, "last_outbound_at", None)
    if last_inbound and (last_outbound is None or last_inbound > last_outbound):
        hours_silent = (time.time() - last_inbound) / 3600
        if hours_silent >= silence_hours:
            sender = getattr(adapter, "last_inbound_sender", "unknown")
            return True, (
                f"Bridge '{bridge_id}' unanswered message from {sender} "
                f"for {hours_silent:.1f}h"
            )
    return False, f"Bridge '{bridge_id}' has no unanswered messages"


# ─── Actions ──────────────────────────────────────────────────────────────────

async def _run_action(
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
    Execute the action path for a fired order.
    Returns (outcome, detail) where outcome is "success"|"failed"|"skipped".
    """
    try:
        if action_type == "notify_ws":
            return await _action_notify_ws(
                action_config, probe_detail, order, ws_gateway
            )
        if action_type == "notify_bridge":
            return await _action_notify_bridge(action_config, probe_detail, order)
        if action_type == "execute_objective":
            return await _action_execute_objective(
                action_config, probe_detail, order, agent_id, orchestrator
            )
        if action_type == "evaluate_goal":
            return await _action_evaluate_goal(action_config)
        if action_type == "log_only":
            return await _action_log_only(probe_detail, order, hlsm_manager)
        if action_type == "pcl_signal":
            return await _action_pcl_signal(
                action_config, probe_detail, order, agent_id, hlsm_manager
            )
        logger.warning("[HB] Unknown action_type: %r", action_type)
        return "skipped", f"Unknown action_type: {action_type}"
    except Exception as exc:
        logger.error(
            "[HB] Action %s raised: %s", action_type, exc, exc_info=True
        )
        return "failed", f"{type(exc).__name__}: {exc}"


async def _action_notify_ws(
    cfg: Dict, probe_detail: str, order: Dict, ws_gateway
) -> Tuple[str, str]:
    if not ws_gateway:
        return "skipped", "No WebSocket gateway available"
    template = cfg.get("message_template", "{label}: {probe_detail}")
    message = (
        template.replace("{label}", order.get("label", ""))
                .replace("{probe_detail}", probe_detail)
    )
    await ws_gateway.broadcast_event(
        "heartbeat.notification",
        {
            "order_id": order.get("id"),
            "label": order.get("label"),
            "message": message,
            "probe_detail": probe_detail,
            "timestamp": time.time(),
        },
    )
    return "success", f"WebSocket notification: {message[:80]}"


async def _action_notify_bridge(
    cfg: Dict, probe_detail: str, order: Dict
) -> Tuple[str, str]:
    from . import services

    bridge_id = cfg.get("bridge_id", "")
    recipient = cfg.get("recipient", "")
    template = cfg.get("message_template", "{label}: {probe_detail}")
    message = (
        template.replace("{label}", order.get("label", ""))
                .replace("{probe_detail}", probe_detail)
    )
    if not bridge_id:
        return "skipped", "No bridge_id in action_config"
    adapter = services.channel_registry.get(bridge_id) if services.channel_registry else None
    if not adapter:
        return "failed", f"Bridge '{bridge_id}' not found"
    try:
        result = await adapter.send_message(recipient=recipient, content=message)
        if isinstance(result, dict) and result.get("status") == "success":
            return "success", f"Sent via {bridge_id} to {recipient}"
        return "failed", str(result)
    except Exception as exc:
        logger.error("[HB] notify_bridge error: %s", exc, exc_info=True)
        return "failed", str(exc)


async def _action_execute_objective(
    cfg: Dict,
    probe_detail: str,
    order: Dict,
    agent_id: Optional[str],
    orchestrator,
) -> Tuple[str, str]:
    if not orchestrator:
        return "skipped", "No orchestrator available"
    template = cfg.get(
        "objective_template",
        f"[Heartbeat: {order.get('label', 'Order')}] {{probe_detail}}",
    )
    objective = template.replace("{probe_detail}", probe_detail)
    autonomy = cfg.get("autonomy", "RESTRICTED")
    if agent_id:
        objective = f"[Agent:{agent_id}] {objective}"
    try:
        result = await orchestrator.execute_objective(
            objective=objective, autonomy=autonomy
        )
        status = (
            result.get("status", "unknown") if isinstance(result, dict) else str(result)
        )
        outcome = "success" if "fail" not in status.lower() else "failed"
        return outcome, f"Executed → {status}: {objective[:80]}"
    except Exception as exc:
        logger.error("[HB] execute_objective error: %s", exc, exc_info=True)
        return "failed", str(exc)


async def _action_evaluate_goal(cfg: Dict) -> Tuple[str, str]:
    from . import services

    goal_id = cfg.get("goal_id")
    if not goal_id:
        return "skipped", "No goal_id in action_config"
    if not getattr(services, "goal_engine", None):
        return "skipped", "GoalsEngine not available"
    try:
        result = await services.goal_engine.evaluate_progress(int(goal_id))
        return "success", f"Goal {goal_id} evaluated: {result}"
    except Exception as exc:
        logger.error("[HB] evaluate_goal error: %s", exc, exc_info=True)
        return "failed", str(exc)


async def _action_log_only(
    probe_detail: str, order: Dict, hlsm_manager
) -> Tuple[str, str]:
    if not hlsm_manager:
        return "skipped", "Memory manager not available"
    content = f"[Heartbeat Log] {order.get('label', '')}: {probe_detail}"
    try:
        await hlsm_manager.store(
            content=content,
            metadata={"source": "heartbeat_log", "order_id": order.get("id")},
        )
        return "success", f"Logged to memory: {content[:80]}"
    except Exception as exc:
        logger.error("[HB] log_only error: %s", exc, exc_info=True)
        return "failed", str(exc)


async def _action_pcl_signal(
    cfg: Dict,
    probe_detail: str,
    order: Dict,
    agent_id: Optional[str],
    hlsm_manager,
) -> Tuple[str, str]:
    """
    Store a structured PCL signal to H-LSM memory with source='heartbeat_signal'.
    The PCL HeartbeatSignalDetector reads these entries on its next cycle.
    """
    if not hlsm_manager:
        return "skipped", "Memory manager not available"

    signal_label = cfg.get("signal_label", order.get("label", "heartbeat_signal"))
    priority = int(cfg.get("priority", 3))
    agent_tag = f"[Agent:{agent_id}] " if agent_id else ""
    order_id = order.get("id", "?")

    content = (
        f"[PCL_SIGNAL] {agent_tag}{signal_label}: {probe_detail} "
        f"(priority={priority}, order_id={order_id})"
    )
    try:
        await hlsm_manager.store(
            content=content,
            metadata={
                "source": "heartbeat_signal",
                "order_id": order_id,
                "agent_id": agent_id,
                "priority": priority,
                "signal_label": signal_label,
            },
        )
        logger.info("[HB] PCL signal stored: %s", content[:100])
        return "success", f"PCL signal stored: {signal_label}"
    except Exception as exc:
        logger.error("[HB] pcl_signal error: %s", exc, exc_info=True)
        return "failed", str(exc)


# ─── HeartbeatDaemon ──────────────────────────────────────────────────────────

class HeartbeatDaemon:
    """
    Upgraded HeartbeatDaemon.

    Constructor signature is backward-compatible with orchestrator.py:
        HeartbeatDaemon(orchestrator, vault[, interval_seconds=900])

    The db_engine is resolved lazily from the module-level `database.engine`
    to avoid a circular import at construction time.
    """

    def __init__(
        self,
        orchestrator,
        vault,
        interval_seconds: int = 900,
        db_engine=None
    ):
        self.orchestrator = orchestrator
        self.vault = vault
        self.default_interval_minutes = interval_seconds // 60
        self.quiet_start: int = 22       # UTC hour
        self.quiet_end: int = 7          # UTC hour
        self.ws_gateway = None
        self._hlsm = None               # Injected by services.py after init
        self.db_engine = db_engine      # Allow injection for tests
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = get_logger("Heartbeat")
        self._dream_orchestrator = None

    def inject_hlsm(self, hlsm, router=None, settings=None) -> None:
        """Called by services.py after HLSMManager is initialised."""
        self._hlsm = hlsm
        self._dream_orchestrator = SleepStateOrchestrator(hlsm, router, settings)

    def _get_db(self):
        if self.db_engine:
            return self.db_engine
        from .database import engine as shared_engine
        return shared_engine

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        self.logger.info("[HB] Heartbeat Daemon started (6-path mode)")
        self._task = asyncio.create_task(self._tick_loop())
        await self._task  # keeps the coroutine alive — matches original behaviour

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
        while self._running:
            try:
                # [ PPN-011 ] Sleep State Evaluation (Dream Cycle)
                from . import services
                if getattr(services, "ace_engine", None):
                    current_affect = services.ace_engine.get_affective_state()
                    
                    if self._dream_orchestrator and await self._dream_orchestrator.evaluate_sleep_trigger(current_affect):
                        # Trigger the dream cycle, which suspends normal polling
                        await self._dream_orchestrator.trigger_dream_cycle()
                
                if not (self._dream_orchestrator and self._dream_orchestrator.is_dreaming):
                    await self._evaluate_all_orders()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.logger.error("[HB] Tick error: %s", exc, exc_info=True)
            try:
                await asyncio.sleep(TICK_SECONDS)
            except asyncio.CancelledError:
                break

    # ─── Quiet hours ──────────────────────────────────────────────────────────

    def _is_quiet_hours(self) -> bool:
        now_h = datetime.now(timezone.utc).hour
        if self.quiet_start > self.quiet_end:  # crosses midnight
            return now_h >= self.quiet_start or now_h < self.quiet_end
        return self.quiet_start <= now_h < self.quiet_end

    # ─── Order loading ────────────────────────────────────────────────────────

    async def _load_root_orders(self) -> List[Dict]:
        try:
            if self.vault:
                manifest_data = await self.vault.retrieve_secret("soul_manifest")
                return [
                    o for o in _load_orders_from_manifest(manifest_data)
                    if o.get("active", False)
                ]
        except Exception as exc:
            self.logger.error(
                "[HB] Failed to load root orders: %s", exc, exc_info=True
            )
        return []

    def _load_agent_orders(self) -> List[Tuple[str, Dict]]:
        """Return [(agent_id, order_dict)] for all ACTIVE agents with orders."""
        result: List[Tuple[str, Dict]] = []
        try:
            db = self._get_db()
            with Session(db) as session:
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
                except json.JSONDecodeError as exc:
                    self.logger.warning(
                        "[HB] Agent %s has invalid heartbeat_orders JSON: %s",
                        agent.id,
                        exc,
                    )
        except Exception as exc:
            self.logger.error(
                "[HB] Failed to load agent orders: %s", exc, exc_info=True
            )
        return result

    # ─── Due-check ────────────────────────────────────────────────────────────

    def _is_order_due(self, order: Dict, agent_id: Optional[str]) -> bool:
        interval_secs = (
            int(order.get("interval_minutes", self.default_interval_minutes)) * 60
        )
        order_id = order.get("id", "")
        try:
            db = self._get_db()
            with Session(db) as session:
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
                return True
            return (time.time() - last.fired_at) >= interval_secs
        except Exception as exc:
            self.logger.debug("[HB] Due check error for %s: %s", order_id, exc)
            return True  # fire on error to avoid silent stalls

    # ─── Single order execution ───────────────────────────────────────────────

    async def _run_order(self, order: Dict, agent_id: Optional[str]) -> None:
        order_id = order.get("id", "?")
        label = order.get("label", "Unnamed")
        probe_type = order.get("probe_type", "task_deadline")
        probe_config = order.get("probe_config", {})
        action_type = order.get("action_type", "log_only")
        action_config = order.get("action_config", {})
        tag = f"[Agent:{agent_id}]" if agent_id else "[Root]"

        self.logger.info(
            "[HB] %s Running '%s' (%s → %s)", tag, label, probe_type, action_type
        )

        fired, probe_detail = await _run_probe(probe_type, probe_config, agent_id)

        if not fired:
            self.logger.debug(
                "[HB] %s '%s': no change — %s", tag, label, probe_detail
            )
            self._persist_outcome(
                order_id, agent_id, probe_type, action_type, "no_change", probe_detail
            )
            return

        self.logger.info("[HB] %s '%s' FIRED: %s", tag, label, probe_detail)

        # Quiet hours: suppress notification-only actions
        if self._is_quiet_hours() and action_type in ("notify_ws", "notify_bridge"):
            self.logger.info(
                "[HB] %s Quiet hours — suppressing notification '%s'", tag, label
            )
            self._persist_outcome(
                order_id, agent_id, probe_type, action_type, "skipped", "quiet_hours"
            )
            return

        outcome, detail = await _run_action(
            action_type=action_type,
            action_config=action_config,
            probe_detail=probe_detail,
            order=order,
            agent_id=agent_id,
            orchestrator=self.orchestrator,
            ws_gateway=self.ws_gateway,
            hlsm_manager=self._hlsm,
        )
        signal_stored = action_type == "pcl_signal" and outcome == "success"
        self._persist_outcome(
            order_id, agent_id, probe_type, action_type, outcome, detail, signal_stored
        )
        self.logger.info("[HB] %s '%s': %s — %s", tag, label, outcome, detail[:100])

    def _persist_outcome(
        self,
        order_id: str,
        agent_id: Optional[str],
        probe_type: str,
        action_type: str,
        outcome: str,
        detail: str,
        signal_stored: bool = False,
    ) -> None:
        record = HeartbeatOrderRecord(
            order_id=order_id,
            agent_id=agent_id,
            fired_at=time.time(),
            probe_type=probe_type,
            action_type=action_type,
            outcome=outcome,
            detail=(detail or "")[:500],
            signal_stored=signal_stored,
        )
        try:
            db = self._get_db()
            with Session(db) as session:
                session.add(record)
                session.commit()
        except Exception as exc:
            self.logger.error(
                "[HB] Failed to persist outcome for %s: %s", order_id, exc,
                exc_info=True,
            )

    # ─── Main evaluation loop ─────────────────────────────────────────────────

    async def _evaluate_all_orders(self) -> None:
        # Alive pulse
        if self.ws_gateway:
            asyncio.create_task(
                self.ws_gateway.broadcast_event(
                    "system.heartbeat",
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "NOMINAL",
                    },
                )
            )

        root_orders = await self._load_root_orders()
        agent_orders = self._load_agent_orders()
        all_orders: List[Tuple[Optional[str], Dict]] = (
            [(None, o) for o in root_orders] + agent_orders
        )

        if not all_orders:
            self.logger.debug("[HB] No active orders")
            return

        due = [
            (aid, o)
            for aid, o in all_orders
            if self._is_order_due(o, aid)
        ]

        if not due:
            self.logger.debug(
                "[HB] %d orders loaded, none due yet", len(all_orders)
            )
            return

        self.logger.info("[HB] %d/%d orders due", len(due), len(all_orders))

        sem = asyncio.Semaphore(MAX_CONCURRENT_ORDERS)

        async def run_guarded(aid: Optional[str], o: Dict) -> None:
            async with sem:
                await self._run_order(o, aid)

        results = await asyncio.gather(
            *[run_guarded(aid, o) for aid, o in due], return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                self.logger.error("[HB] Order raised: %s", r, exc_info=True)

    # ─── UI introspection ─────────────────────────────────────────────────────

    def get_order_history(
        self,
        order_id: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        try:
            db = self._get_db()
            with Session(db) as session:
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
        except Exception as exc:
            self.logger.error(
                "[HB] get_order_history error: %s", exc, exc_info=True
            )
            return []
