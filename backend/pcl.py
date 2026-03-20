"""
Proactive Cognition Loop (PCL)
==============================

A persistent background cognitive process that continuously observes the
agent's environment, builds a world model, detects opportunities and gaps,
and takes calibrated proactive action without waiting for user input.

Architecture:
    OBSERVE → MODEL → DETECT → JUDGE → ACT/NOTIFY

This is architecturally distinct from the HeartbeatDaemon:
  - Heartbeat: scheduled file-polling daemon (health pulse + TASKS.md watcher)
  - PCL: cognitive reasoning loop with world model (proactive intelligence)

Both run concurrently. The Heartbeat remains as the system health primitive.
The PCL is the proactive intelligence layer.

Prerequisites:
    - HLSMManager must be initialized (H-LSM memory integration)
    - GoalsEngine must be initialized
    - AffectiveEngine (ACE) must be initialized
    - ExecutiveOrchestrator must be initialized
    - JsonRpcGateway (ws_gateway) must be initialized for notifications

Integration point: services.init_services() calls pcl.start()
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select, col

from .logging_config import get_logger
from .models import (
    GoalRecord, PCLOpportunity, PCLWorldModelSnapshot, TaskRecord
)

logger = get_logger("PCL")

# ─── Configuration ────────────────────────────────────────────────────────────

PCL_CYCLE_INTERVAL: float = 300.0          # 5 minutes between cycles
PCL_QUIET_START_HOUR: int = 22             # Quiet hours start (UTC)
PCL_QUIET_END_HOUR: int = 7               # Quiet hours end (UTC)
PCL_MAX_OPPORTUNITIES_PER_CYCLE: int = 3   # Max opportunities actioned per cycle
PCL_SNAPSHOT_RETENTION_HOURS: float = 48.0 # How long to keep world model snapshots
PCL_OPPORTUNITY_RETENTION_HOURS: float = 168.0  # 7 days


# ─── World Model Dataclasses ──────────────────────────────────────────────────

@dataclass
class GoalSnapshot:
    """Lightweight snapshot of a goal for world model construction."""
    id: int
    title: str
    description: str
    priority: str
    status: str
    metric_current: float
    metric_target: Optional[float]
    days_since_update: float
    has_deadline: bool
    days_to_deadline: Optional[float]
    l1_memory_count: int            # H-LSM L1 entries referencing this goal


@dataclass
class BridgeThread:
    """An unanswered inbound bridge conversation."""
    bridge_id: str
    sender: str
    last_message: str
    hours_unanswered: float


@dataclass
class WorldModel:
    """
    Complete snapshot of the agent's world at a point in time.
    Built from all available signal sources every PCL cycle.
    """
    # Goal domain
    active_goals: List[GoalSnapshot] = field(default_factory=list)
    goals_at_risk: List[GoalSnapshot] = field(default_factory=list)

    # Memory domain
    unresolved_threads: List[str] = field(default_factory=list)
    recent_learnings: List[str] = field(default_factory=list)
    recurring_topics: List[str] = field(default_factory=list)

    # Affective domain
    current_psi: float = 0.0
    current_valence: float = 0.5
    current_flow_mode: str = "STANDARD"
    biometric_available: bool = False

    # Bridge domain
    pending_bridge_messages: int = 0
    unanswered_threads: List[BridgeThread] = field(default_factory=list)

    # System domain
    recent_failures: List[str] = field(default_factory=list)
    error_rate_trend: str = "stable"
    last_successful_run_hours_ago: Optional[float] = None

    # Heartbeat domain
    heartbeat_signals: List[Dict[str, Any]] = field(default_factory=list)

    # Meta
    built_at: float = field(default_factory=time.time)
    cycle_number: int = 0


# ─── Opportunity Dataclass ────────────────────────────────────────────────────

@dataclass
class Opportunity:
    """
    A detected proactive opportunity ready for judge evaluation.
    Mirrors the PCLOpportunity SQLModel but as an in-memory dataclass
    for fast manipulation before persistence.
    """
    id: str                           # Deterministic: sha256(detector+condition)[:16]
    detector_name: str
    title: str
    description: str
    priority: int                     # 1=critical, 5=low
    confidence: float                 # 0.0–1.0
    recommended_action: str           # "execute" | "notify" | "defer"
    objective: str = ""               # Filled when action=execute
    notification_body: str = ""       # Filled when action=notify
    autonomy_level: str = "RESTRICTED"
    requires_approval: bool = False
    cooldown_minutes: int = 60
    affects_goal_id: Optional[int] = None

    @staticmethod
    def make_id(detector_name: str, condition_key: str) -> str:
        """Deterministic ID from detector + condition so duplicates can be detected."""
        raw = f"{detector_name}:{condition_key}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── Base Detector ────────────────────────────────────────────────────────────

class BaseDetector:
    """
    Abstract base for all PCL detectors.
    Each detector inspects the world model and optionally returns an Opportunity.
    Detectors are pure functions of the world model — they never modify it.
    """
    name: str = "base"

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        """
        Inspect the world model and return an Opportunity if a condition is met,
        or None if no action is warranted.
        """
        raise NotImplementedError


# ─── Built-in Detectors ───────────────────────────────────────────────────────

class GoalStallDetector(BaseDetector):
    """
    Detects active goals that have not had a progress update in > 48 hours.
    Fires a notification to prompt the user to review or act.
    """
    name = "GoalStallDetector"
    STALL_HOURS = 48.0

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        stalled = [
            g for g in world.active_goals
            if g.days_since_update * 24 > self.STALL_HOURS
            and g.status == "active"
            and (g.metric_target is None or g.metric_current < g.metric_target)
        ]
        if not stalled:
            return None

        # Pick the highest-priority stalled goal
        priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        stalled.sort(key=lambda g: priority_order.get(g.priority, 4))
        top = stalled[0]

        condition_key = f"goal_stall:{top.id}:{int(top.days_since_update)}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Goal stalled: {top.title}",
            description=(
                f"'{top.title}' ({top.priority}) has had no progress update "
                f"for {top.days_since_update * 24:.0f} hours. "
                f"Current progress: {top.metric_current:.0f}% of "
                f"{top.metric_target or 100:.0f}%."
            ),
            priority=2 if top.priority in ("URGENT", "HIGH") else 3,
            confidence=0.85,
            recommended_action="notify",
            notification_body=(
                f"📊 Goal Check-In: '{top.title}' hasn't moved in "
                f"{top.days_since_update * 24:.0f}h. "
                f"Progress: {top.metric_current:.0f}%. Should I take action?"
            ),
            cooldown_minutes=360,  # 6 hours
            affects_goal_id=top.id,
        )


class GoalDeadlineDetector(BaseDetector):
    """
    Detects goals approaching their deadline with insufficient progress.
    Fires an execute action to make autonomous progress, or a critical notification.
    """
    name = "GoalDeadlineDetector"
    URGENT_HOURS = 24.0
    WARNING_HOURS = 72.0
    PROGRESS_THRESHOLD = 0.80   # 80% complete = not at risk

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        at_risk = [
            g for g in world.goals_at_risk
            if g.has_deadline
            and g.days_to_deadline is not None
            and g.days_to_deadline * 24 <= self.WARNING_HOURS
            and (g.metric_current / max(g.metric_target or 100, 1)) < self.PROGRESS_THRESHOLD
        ]
        if not at_risk:
            return None

        top = min(at_risk, key=lambda g: g.days_to_deadline or 999)
        hours_left = (top.days_to_deadline or 0) * 24
        progress_pct = (top.metric_current / max(top.metric_target or 100, 1)) * 100
        is_critical = hours_left <= self.URGENT_HOURS

        condition_key = f"goal_deadline:{top.id}:{int(hours_left)}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Deadline approaching: {top.title}",
            description=(
                f"'{top.title}' is due in {hours_left:.0f}h with only "
                f"{progress_pct:.0f}% complete."
            ),
            priority=1 if is_critical else 2,
            confidence=0.90,
            recommended_action="execute" if is_critical else "notify",
            objective=(
                f"The goal '{top.title}' is due in {hours_left:.0f} hours "
                f"and is only {progress_pct:.0f}% complete. "
                f"Goal description: {top.description}. "
                f"Take the most impactful autonomous action to advance this goal. "
                f"Focus on high-leverage tasks that can be completed quickly."
            ) if is_critical else "",
            notification_body=(
                f"⏰ Deadline Alert: '{top.title}' is due in {hours_left:.0f}h "
                f"({progress_pct:.0f}% done). Should I prioritize this now?"
            ),
            autonomy_level="SEMI_AUTONOMOUS" if is_critical else "RESTRICTED",
            cooldown_minutes=120,
            affects_goal_id=top.id,
        )


class HeartbeatSignalDetector(BaseDetector):
    """
    Detects structured signals emitted by the HeartbeatDaemon (e.g., from
    URL fetch probes, file watches, or custom PCL signal actions).
    Consumes entries from H-LSM L1 memory tagged with 'heartbeat_signal'.
    """
    name = "HeartbeatSignalDetector"

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        if not hasattr(world, 'heartbeat_signals') or not world.heartbeat_signals:
            return None

        # Filter signals that haven't been actioned (simple heuristic: priority <= 3)
        signals = [s for s in world.heartbeat_signals if s.get("priority", 3) <= 3]
        if not signals:
            return None

        # Pick the highest priority/most recent
        sig = sorted(signals, key=lambda x: (x.get("priority", 3), -x.get("timestamp", 0)))[0]

        label = sig.get("label", "Heartbeat Signal")
        detail = sig.get("detail", "")
        prio = sig.get("priority", 3)

        condition_key = f"hb_sig:{sig.get('order_id', 'unknown')}:{sig.get('timestamp', 0)}"

        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Heartbeat: {label}",
            description=f"Signal from heartbeat order '{label}': {detail}",
            priority=prio,
            confidence=0.98,  # High confidence as it's a direct system signal
            recommended_action="execute" if prio <= 2 else "notify",
            objective=f"Process heartbeat signal '{label}': {detail}. Take appropriate action based on the reported state.",
            notification_body=f"💓 Heartbeat Alert [{label}]: {detail}",
            autonomy_level="SEMI_AUTONOMOUS" if prio <= 2 else "RESTRICTED",
            cooldown_minutes=30,
        )


class UnresolvedBridgeDetector(BaseDetector):
    """
    Detects inbound bridge messages that have not received an agent reply
    for more than the configured threshold (default 4 hours).
    Fires an execute action to respond.
    """
    name = "UnresolvedBridgeDetector"
    UNANSWERED_HOURS = 4.0

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        old_threads = [
            t for t in world.unanswered_threads
            if t.hours_unanswered >= self.UNANSWERED_HOURS
        ]
        if not old_threads:
            return None

        # Sort by how long they've been waiting
        old_threads.sort(key=lambda t: t.hours_unanswered, reverse=True)
        oldest = old_threads[0]

        condition_key = f"bridge_unresolved:{oldest.bridge_id}:{oldest.sender}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Unanswered message: {oldest.bridge_id} from {oldest.sender}",
            description=(
                f"Message on {oldest.bridge_id} from {oldest.sender} "
                f"has been unanswered for {oldest.hours_unanswered:.1f}h. "
                f"Content: {oldest.last_message[:150]}"
            ),
            priority=2,
            confidence=0.95,
            recommended_action="execute",
            objective=(
                f"Respond to the unanswered {oldest.bridge_id} message from "
                f"{oldest.sender} (waiting {oldest.hours_unanswered:.1f}h). "
                f"Message: '{oldest.last_message}'. "
                f"Provide a helpful, appropriate response."
            ),
            autonomy_level="SEMI_AUTONOMOUS",
            cooldown_minutes=240,
        )


class RecurringTopicDetector(BaseDetector):
    """
    Detects topics that appear repeatedly in H-LSM episodic memory
    without a corresponding resolution or closure signal.
    Surfaces as a notification for the user to address.
    """
    name = "RecurringTopicDetector"
    MIN_OCCURRENCES = 3

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        if not world.recurring_topics:
            return None

        topic = world.recurring_topics[0]  # Most frequent first
        condition_key = f"recurring_topic:{hashlib.sha256(topic.encode()).hexdigest()[:8]}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Recurring pattern: {topic[:60]}",
            description=(
                f"The topic '{topic}' has appeared {self.MIN_OCCURRENCES}+ times "
                f"in recent memory without resolution. This may indicate an "
                f"unresolved issue or recurring need."
            ),
            priority=3,
            confidence=0.70,
            recommended_action="notify",
            notification_body=(
                f"🔄 Pattern Detected: '{topic[:80]}' keeps coming up. "
                f"Want me to address this systematically?"
            ),
            cooldown_minutes=720,  # 12 hours
        )


class TaskFailurePatternDetector(BaseDetector):
    """
    Detects when the same task action type has failed multiple times
    in the past 24 hours, indicating a systemic problem.
    """
    name = "TaskFailurePatternDetector"
    FAILURE_THRESHOLD = 3

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        if len(world.recent_failures) < self.FAILURE_THRESHOLD:
            return None

        # Count failures by action type
        action_counts: Dict[str, int] = {}
        for failure in world.recent_failures:
            action_counts[failure] = action_counts.get(failure, 0) + 1

        worst_action = max(action_counts, key=action_counts.get)
        worst_count = action_counts[worst_action]

        if worst_count < self.FAILURE_THRESHOLD:
            return None

        condition_key = f"failure_pattern:{worst_action}:{worst_count}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Repeated failures: {worst_action} ({worst_count}×)",
            description=(
                f"The '{worst_action}' adapter has failed {worst_count} times "
                f"in the last 24 hours. This suggests a configuration issue, "
                f"service outage, or permission problem."
            ),
            priority=2,
            confidence=0.80,
            recommended_action="notify",
            notification_body=(
                f"⚠️ System Alert: '{worst_action}' has failed {worst_count} times "
                f"today. This may need attention."
            ),
            cooldown_minutes=180,
        )


class MemoryGapDetector(BaseDetector):
    """
    Detects active goals that have zero H-LSM episodic memories in the
    past 7 days — indicating the agent has been working on nothing related
    to that goal and it may have been forgotten.
    """
    name = "MemoryGapDetector"
    GAP_DAYS = 7.0

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        forgotten = [
            g for g in world.active_goals
            if g.l1_memory_count == 0
            and g.days_since_update > self.GAP_DAYS
            and g.status == "active"
        ]
        if not forgotten:
            return None

        top = forgotten[0]
        condition_key = f"memory_gap:{top.id}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Forgotten goal: {top.title}",
            description=(
                f"Active goal '{top.title}' has no activity in memory "
                f"for {top.days_since_update:.0f} days. "
                f"It may have been deprioritized or forgotten."
            ),
            priority=3,
            confidence=0.75,
            recommended_action="notify",
            notification_body=(
                f"💭 Memory Gap: Active goal '{top.title}' has had no "
                f"activity for {top.days_since_update:.0f} days. "
                f"Still relevant?"
            ),
            cooldown_minutes=1440,  # 24 hours
            affects_goal_id=top.id,
        )


class PeakOpportunityDetector(BaseDetector):
    """
    Detects when the user is in PEAK_PERFORMANCE flow mode with no active
    execution and high-priority goals pending. Proactively starts work.
    This is the most assertive detector — it initiates execution unprompted.
    """
    name = "PeakOpportunityDetector"

    def detect(self, world: WorldModel) -> Optional[Opportunity]:
        if world.current_flow_mode != "PEAK_PERFORMANCE":
            return None

        high_priority_pending = [
            g for g in world.active_goals
            if g.priority in ("URGENT", "HIGH")
            and g.status == "active"
            and (g.metric_current / max(g.metric_target or 100, 1)) < 0.9
        ]
        if not high_priority_pending:
            return None

        top = high_priority_pending[0]
        condition_key = f"peak_opportunity:{top.id}:{int(time.time() // 3600)}"
        return Opportunity(
            id=Opportunity.make_id(self.name, condition_key),
            detector_name=self.name,
            title=f"Peak performance: advance '{top.title}'",
            description=(
                f"User is in PEAK_PERFORMANCE flow mode. "
                f"High-priority goal '{top.title}' is {top.metric_current:.0f}% complete. "
                f"Optimal moment to advance it autonomously."
            ),
            priority=3,
            confidence=0.72,
            recommended_action="execute",
            objective=(
                f"The user is currently in peak performance state. "
                f"Autonomously advance the high-priority goal: '{top.title}'. "
                f"Description: {top.description}. "
                f"Current progress: {top.metric_current:.0f}% of {top.metric_target or 100:.0f}%. "
                f"Take the single most impactful action that can be completed now."
            ),
            autonomy_level="SEMI_AUTONOMOUS",
            cooldown_minutes=120,
            affects_goal_id=top.id,
        )


# ─── Intervention Judge ───────────────────────────────────────────────────────

class InterventionJudge:
    """
    Applies the five-rule gate to each opportunity before it is actioned.
    All five rules must pass. Returns (approved: bool, reason: str).
    """

    def __init__(self, db_engine, quiet_start: int = PCL_QUIET_START_HOUR,
                 quiet_end: int = PCL_QUIET_END_HOUR):
        self.db_engine = db_engine
        self.quiet_start = quiet_start
        self.quiet_end = quiet_end

    def evaluate(self, opp: Opportunity, world: WorldModel) -> Tuple[bool, str]:
        """Returns (approved, reason)."""

        # Rule 1 — ACE Flow Gate
        flow_gate = self._check_flow_gate(opp, world.current_flow_mode)
        if not flow_gate[0]:
            return flow_gate

        # Rule 2 — Quiet Hours Gate
        quiet_gate = self._check_quiet_hours(opp)
        if not quiet_gate[0]:
            return quiet_gate

        # Rule 3 — Cooldown Gate
        cooldown_gate = self._check_cooldown(opp)
        if not cooldown_gate[0]:
            return cooldown_gate

        # Rule 4 — Confidence Threshold
        confidence_gate = self._check_confidence(opp)
        if not confidence_gate[0]:
            return confidence_gate

        # Rule 5 — Deduplication Gate
        dedup_gate = self._check_deduplication(opp)
        if not dedup_gate[0]:
            return dedup_gate

        return True, "approved"

    def _check_flow_gate(self, opp: Opportunity, flow_mode: str) -> Tuple[bool, str]:
        if flow_mode == "RECOVERY_MODE":
            return False, f"ACE: RECOVERY_MODE — all PCL actions suppressed"
        if flow_mode == "DEEP_WORK" and opp.priority > 1:
            return False, f"ACE: DEEP_WORK — only P1 opportunities allowed (this is P{opp.priority})"
        return True, "flow_gate_passed"

    def _check_quiet_hours(self, opp: Opportunity) -> Tuple[bool, str]:
        from datetime import datetime, timezone
        now_hour = datetime.now(timezone.utc).hour
        in_quiet = False
        if self.quiet_start > self.quiet_end:  # crosses midnight
            in_quiet = now_hour >= self.quiet_start or now_hour < self.quiet_end
        else:
            in_quiet = self.quiet_start <= now_hour < self.quiet_end

        if in_quiet and not (opp.priority == 1 and opp.recommended_action == "execute"):
            return False, f"Quiet hours ({self.quiet_start}:00–{self.quiet_end}:00 UTC)"
        return True, "quiet_hours_passed"

    def _check_cooldown(self, opp: Opportunity) -> Tuple[bool, str]:
        cutoff = time.time() - (opp.cooldown_minutes * 60)
        with Session(self.db_engine) as session:
            recent = session.exec(
                select(PCLOpportunity)
                .where(
                    PCLOpportunity.id == opp.id,
                    PCLOpportunity.actioned == True,
                    PCLOpportunity.actioned_at > cutoff,
                )
            ).first()
        if recent:
            elapsed = (time.time() - (recent.actioned_at or 0)) / 60
            return False, f"Cooldown: actioned {elapsed:.0f}m ago (cooldown={opp.cooldown_minutes}m)"
        return True, "cooldown_passed"

    def _check_confidence(self, opp: Opportunity) -> Tuple[bool, str]:
        threshold = 0.75 if opp.recommended_action == "execute" else 0.60
        if opp.confidence < threshold:
            return False, (
                f"Confidence too low: {opp.confidence:.2f} < {threshold:.2f} "
                f"(required for {opp.recommended_action})"
            )
        return True, "confidence_passed"

    def _check_deduplication(self, opp: Opportunity) -> Tuple[bool, str]:
        cutoff_24h = time.time() - 86400
        with Session(self.db_engine) as session:
            recent = session.exec(
                select(PCLOpportunity)
                .where(
                    PCLOpportunity.id == opp.id,
                    PCLOpportunity.detected_at > cutoff_24h,
                    PCLOpportunity.outcome.in_(["success", "ignored"]),
                )
            ).first()
        if recent:
            return False, f"Deduplicated: same opportunity actioned/ignored within 24h"
        return True, "deduplication_passed"


# ─── PCL Engine ───────────────────────────────────────────────────────────────

class ProactiveCognitionLoop:
    """
    Main PCL orchestrator. Runs continuously in the background.

    Instantiated by services.init_services() and started via start().
    Stopped gracefully via stop() during shutdown.

    All five PCL stages are implemented as separate methods for testability.
    """

    def __init__(
        self,
        db_engine,
        orchestrator,
        ace_engine,
        goal_engine,
        hlsm_manager,
        ws_gateway=None,
        channel_registry: Optional[Dict] = None,
        settings=None,
        cycle_interval: float = PCL_CYCLE_INTERVAL,
    ):
        self.db_engine = db_engine
        self.orchestrator = orchestrator
        self.ace = ace_engine
        self.goal_engine = goal_engine
        self.hlsm = hlsm_manager
        self.ws_gateway = ws_gateway
        self.channel_registry = channel_registry or {}
        self.settings = settings
        self.cycle_interval = cycle_interval

        # Detector registry — order determines priority in ties
        self.detectors: List[BaseDetector] = [
            GoalDeadlineDetector(),
            UnresolvedBridgeDetector(),
            GoalStallDetector(),
            TaskFailurePatternDetector(),
            RecurringTopicDetector(),
            MemoryGapDetector(),
            PeakOpportunityDetector(),
            HeartbeatSignalDetector(),
        ]

        self.judge = InterventionJudge(db_engine)
        self._cycle_number: int = 0
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

        logger.info(
            f"[PCL] Initialized with {len(self.detectors)} detectors, "
            f"cycle_interval={cycle_interval}s"
        )

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the PCL background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[PCL] Started")

    async def stop(self) -> None:
        """Gracefully stop the PCL."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[PCL] Stopped")

    async def _loop(self) -> None:
        """Main run loop. Executes one cycle then sleeps for cycle_interval."""
        while self._running:
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PCL] Cycle error: {e}", exc_info=True)
                # Back off 60s on unexpected error to avoid tight error loops
                await asyncio.sleep(60.0)
                continue
            try:
                await asyncio.sleep(self.cycle_interval)
            except asyncio.CancelledError:
                break

    # ─── Stage 1: OBSERVE + MODEL ─────────────────────────────────────────────

    async def build_world_model(self) -> WorldModel:
        """
        Stage 1+2: Observe all signal sources and build the world model.
        All I/O is async. Failures in individual sources degrade gracefully.
        """
        self._cycle_number += 1
        world = WorldModel(built_at=time.time(), cycle_number=self._cycle_number)

        await asyncio.gather(
            self._observe_goals(world),
            self._observe_ace(world),
            self._observe_memory(world),
            self._observe_bridges(world),
            self._observe_system(world),
            self._observe_heartbeat(world),
            return_exceptions=True,
        )

        return world

    async def _observe_goals(self, world: WorldModel) -> None:
        """Observe the GoalsEngine database."""
        try:
            all_goals = await self.goal_engine.list_goals(status="active")
            now = time.time()

            for goal in all_goals:
                updated = goal.updated_at
                if updated:
                    days_since = (now - updated.timestamp()) / 86400
                else:
                    days_since = (now - goal.created_at.timestamp()) / 86400 if goal.created_at else 0

                # Check if there's a deadline in the description or title
                # (GoalRecord doesn't have a deadline field yet — extract from description)
                has_deadline = False
                days_to_deadline = None
                import re
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', goal.description or "")
                if date_match:
                    try:
                        from datetime import datetime, timezone
                        deadline = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        days_to_deadline = (deadline.timestamp() - now) / 86400
                        has_deadline = True
                    except ValueError:
                        pass

                # Count L1 memory entries for this goal
                l1_count = await self._count_l1_memories_for_goal(goal.title)

                snapshot = GoalSnapshot(
                    id=goal.id,
                    title=goal.title,
                    description=goal.description or "",
                    priority=goal.priority,
                    status=goal.status,
                    metric_current=goal.metric_current,
                    metric_target=goal.metric_target,
                    days_since_update=days_since,
                    has_deadline=has_deadline,
                    days_to_deadline=days_to_deadline,
                    l1_memory_count=l1_count,
                )
                world.active_goals.append(snapshot)

                # At-risk: approaching deadline or long stall
                if (has_deadline and days_to_deadline is not None and days_to_deadline < 3) \
                        or (days_since > 2 and goal.priority in ("URGENT", "HIGH")):
                    world.goals_at_risk.append(snapshot)

        except Exception as e:
            logger.error(f"[PCL] Goal observation failed: {e}", exc_info=True)

    async def _count_l1_memories_for_goal(self, goal_title: str) -> int:
        """Count L1 episodic entries referencing a goal by title keyword."""
        if not self.hlsm:
            return 0
        try:
            results = await self.hlsm.l1_search(goal_title[:50], limit=20)
            return len(results)
        except Exception:
            return 0

    async def _observe_ace(self, world: WorldModel) -> None:
        """Observe the ACE engine's current affective state."""
        try:
            if not self.ace:
                return
            state = self.ace.get_affective_state()
            world.current_psi = min(1.0, float(state.tension) / 1024.0)
            world.current_valence = min(1.0, float(state.valence) / 1024.0)
            world.current_flow_mode = self.ace.current_state.get("flow_mode", "STANDARD")
            # Biometric available if HRV data has been received recently
            world.biometric_available = float(state.arousal) > 0
        except Exception as e:
            logger.debug(f"[PCL] ACE observation failed: {e}")

    async def _observe_memory(self, world: WorldModel) -> None:
        """Observe H-LSM for recurring topics and unresolved threads."""
        if not self.hlsm:
            return
        try:
            # Get recent L1 entries (last 24h indicator)
            recent = await self.hlsm.l1_get_recent(limit=50)
            now = time.time()
            world.recent_learnings = [
                r.content[:200]
                for r in recent
                if now - r.retention_score * 86400 < 86400  # rough 24h proxy
            ][:10]

            # Detect recurring topics
            topic_counts: Dict[str, int] = {}
            for r in recent:
                prefix = r.content[:50]
                topic_counts[prefix] = topic_counts.get(prefix, 0) + 1
            
            world.recurring_topics = sorted(
                [t for t, c in topic_counts.items() if c >= 2],
                key=lambda x: topic_counts[x],
                reverse=True
            )
        except Exception as e:
            logger.debug(f"[PCL] Memory observation failed: {e}")

    async def _observe_heartbeat(self, world: WorldModel) -> None:
        """Fetch recent heartbeat signals from H-LSM L1."""
        if not self.hlsm:
            return
        try:
            recent = await self.hlsm.l1_search("heartbeat_signal", limit=20)
            now = time.time()
            signals = []
            for r in recent:
                try:
                    data = json.loads(r.content)
                    if isinstance(data, dict) and data.get("type") == "heartbeat_signal":
                        if now - r.timestamp < 3600:
                            signals.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue
            world.heartbeat_signals = signals
        except Exception as e:
            logger.debug(f"[PCL] Heartbeat observation failed: {e}")

    async def _observe_bridges(self, world: WorldModel) -> None:
        """
        Observe connected bridge channels for pending/unanswered messages.
        Inspects the channel_registry for adapters with unread message queues.
        """
        try:
            total_pending = 0
            unanswered = []

            for bridge_id, adapter in self.channel_registry.items():
                # Check if adapter has a pending message count attribute
                pending = getattr(adapter, "pending_message_count", 0)
                total_pending += int(pending)

                # Check for unanswered threads via adapter's last_inbound metadata
                last_inbound = getattr(adapter, "last_inbound_at", None)
                last_outbound = getattr(adapter, "last_outbound_at", None)
                last_sender = getattr(adapter, "last_inbound_sender", "unknown")
                last_body = getattr(adapter, "last_inbound_body", "")

                if last_inbound and (last_outbound is None or last_inbound > last_outbound):
                    hours_unanswered = (time.time() - last_inbound) / 3600
                    if hours_unanswered >= 1.0:  # Only flag if > 1 hour unanswered
                        unanswered.append(BridgeThread(
                            bridge_id=bridge_id,
                            sender=str(last_sender),
                            last_message=str(last_body)[:200],
                            hours_unanswered=hours_unanswered,
                        ))

            world.pending_bridge_messages = total_pending
            world.unanswered_threads = sorted(
                unanswered, key=lambda t: t.hours_unanswered, reverse=True
            )[:5]

        except Exception as e:
            logger.debug(f"[PCL] Bridge observation failed: {e}")

    async def _observe_system(self, world: WorldModel) -> None:
        """Observe recent task execution history for failure patterns."""
        try:
            cutoff_24h = time.time() - 86400
            with Session(self.db_engine) as session:
                from datetime import datetime, timezone
                # Get failed tasks in last 24h
                failed_records = session.exec(
                    select(TaskRecord)
                    .where(
                        TaskRecord.status == "failed",
                        TaskRecord.end_time != None,
                    )
                    .order_by(col(TaskRecord.end_time).desc())
                    .limit(50)
                ).all()

            recent_failures = []
            for record in failed_records:
                if record.end_time:
                    age_seconds = (time.time() - record.end_time.timestamp())
                    if age_seconds <= 86400:
                        recent_failures.append(record.action)

            world.recent_failures = recent_failures

            # Determine error rate trend
            if len(recent_failures) == 0:
                world.error_rate_trend = "stable"
            elif len(recent_failures) < 3:
                world.error_rate_trend = "low"
            elif len(recent_failures) < 8:
                world.error_rate_trend = "increasing"
            else:
                world.error_rate_trend = "spike"

        except Exception as e:
            logger.debug(f"[PCL] System observation failed: {e}")

    # ─── Stage 3: DETECT ──────────────────────────────────────────────────────

    def detect_opportunities(self, world: WorldModel) -> List[Opportunity]:
        """
        Stage 3: Run all detectors against the world model.
        Returns list of raw opportunities (not yet judged).
        """
        opportunities = []
        for detector in self.detectors:
            try:
                result = detector.detect(world)
                if result is not None:
                    opportunities.append(result)
                    logger.debug(
                        f"[PCL] {detector.name} fired: '{result.title}' "
                        f"(P{result.priority}, conf={result.confidence:.2f})"
                    )
            except Exception as e:
                logger.error(f"[PCL] Detector {detector.name} error: {e}", exc_info=True)

        # Sort by priority (1=critical first) then confidence descending
        opportunities.sort(key=lambda o: (o.priority, -o.confidence))
        return opportunities

    # ─── Stage 4: JUDGE ───────────────────────────────────────────────────────

    def judge_opportunities(
        self, opportunities: List[Opportunity], world: WorldModel
    ) -> List[Tuple[Opportunity, str]]:
        """
        Stage 4: Apply the five-rule gate to each opportunity.
        Returns list of (opportunity, reason) tuples that passed all rules.
        Capped at PCL_MAX_OPPORTUNITIES_PER_CYCLE.
        """
        approved = []
        for opp in opportunities:
            passed, reason = self.judge.evaluate(opp, world)
            if passed:
                approved.append((opp, reason))
                logger.info(f"[PCL] Approved: '{opp.title}' ({opp.recommended_action})")
            else:
                logger.debug(f"[PCL] Blocked: '{opp.title}' — {reason}")

        return approved[:PCL_MAX_OPPORTUNITIES_PER_CYCLE]

    # ─── Stage 5: ACT/NOTIFY ──────────────────────────────────────────────────

    async def act_on_opportunities(
        self, approved: List[Tuple[Opportunity, str]], world: WorldModel
    ) -> int:
        """
        Stage 5: Execute approved opportunities via execute or notify pathway.
        Persists each opportunity to DB with outcome tracking.
        Returns count of opportunities actioned.
        """
        actioned = 0
        for opp, _ in approved:
            # Persist to DB before acting (so cooldown works even if action fails)
            db_opp = self._persist_opportunity(opp, world.cycle_number)

            try:
                if opp.recommended_action == "execute":
                    outcome = await self._execute_opportunity(opp)
                elif opp.recommended_action == "notify":
                    outcome = await self._notify_opportunity(opp)
                else:
                    outcome = "deferred"

                self._update_opportunity_outcome(db_opp.id, outcome)
                actioned += 1
                logger.info(f"[PCL] Actioned '{opp.title}': {outcome}")

            except Exception as e:
                logger.error(f"[PCL] Action failed for '{opp.title}': {e}", exc_info=True)
                self._update_opportunity_outcome(db_opp.id, "failure")

        return actioned

    async def _execute_opportunity(self, opp: Opportunity) -> str:
        """Execute an opportunity via the orchestrator."""
        if not self.orchestrator:
            logger.warning("[PCL] No orchestrator — cannot execute")
            return "failure"

        logger.info(f"[PCL] Executing: '{opp.title}'")
        try:
            result = await self.orchestrator.execute_objective(
                objective=opp.objective,
                autonomy=opp.autonomy_level,
            )
            status = result.get("status", "unknown") if isinstance(result, dict) else str(result)

            # Encode the execution to H-LSM so it's remembered
            if self.hlsm:
                await self.hlsm.l1_store(
                    content=f"[PCL Action] {opp.title}: {str(result)[:300]}",
                    source="pcl_action",
                    psi=opp.confidence,
                    topological_importance=2.0 - (opp.priority * 0.2),
                )

            # Broadcast to WebSocket
            if self.ws_gateway:
                asyncio.create_task(self.ws_gateway.broadcast_event("pcl.action_taken", {
                    "title": opp.title,
                    "detector": opp.detector_name,
                    "priority": opp.priority,
                    "status": status,
                }))

            return "success" if "fail" not in status.lower() else "failure"
        except Exception as e:
            logger.error(f"[PCL] Execute failed: {e}", exc_info=True)
            return "failure"

    async def _notify_opportunity(self, opp: Opportunity) -> str:
        """Send a notification via WebSocket and optionally via bridge channel."""
        notification = {
            "id": opp.id,
            "title": opp.title,
            "body": opp.notification_body,
            "priority": opp.priority,
            "detector": opp.detector_name,
            "affects_goal_id": opp.affects_goal_id,
            "timestamp": time.time(),
        }

        # Primary: WebSocket broadcast to UI
        if self.ws_gateway:
            try:
                await self.ws_gateway.broadcast_event("pcl.notification", notification)
                logger.info(f"[PCL] Notified via WebSocket: '{opp.title}'")
            except Exception as e:
                logger.error(f"[PCL] WebSocket notification failed: {e}")

        # Secondary: encode to H-LSM working memory for next context
        if self.hlsm:
            try:
                await self.hlsm.l1_store(
                    content=f"[PCL Notification] {opp.notification_body}",
                    source="pcl_notification",
                    topological_importance=1.5,
                )
            except Exception as e:
                logger.debug(f"[PCL] H-LSM notification store failed: {e}")

        return "success"

    # ─── Persistence Helpers ──────────────────────────────────────────────────

    def _persist_opportunity(self, opp: Opportunity, cycle_number: int) -> PCLOpportunity:
        """Persist an opportunity to the DB before acting on it."""
        db_opp = PCLOpportunity(
            id=opp.id,
            detector_name=opp.detector_name,
            title=opp.title,
            description=opp.description,
            priority=opp.priority,
            confidence=opp.confidence,
            recommended_action=opp.recommended_action,
            objective=opp.objective,
            notification_body=opp.notification_body,
            autonomy_level=opp.autonomy_level,
            requires_approval=opp.requires_approval,
            cooldown_minutes=opp.cooldown_minutes,
            affects_goal_id=opp.affects_goal_id,
            actioned=True,
            actioned_at=time.time(),
            detected_at=time.time(),
            cycle_number=cycle_number,
        )
        with Session(self.db_engine) as session:
            # Upsert: delete existing then insert (SQLite compatible)
            existing = session.get(PCLOpportunity, opp.id)
            if existing:
                session.delete(existing)
                session.commit()
            session.add(db_opp)
            session.commit()
            session.refresh(db_opp)
        return db_opp

    def _update_opportunity_outcome(self, opp_id: str, outcome: str) -> None:
        with Session(self.db_engine) as session:
            opp = session.get(PCLOpportunity, opp_id)
            if opp:
                opp.outcome = outcome
                session.add(opp)
                session.commit()

    def _persist_world_snapshot(
        self, world: WorldModel, opportunities_detected: int, opportunities_actioned: int,
        duration_ms: float
    ) -> None:
        snapshot = PCLWorldModelSnapshot(
            cycle_number=world.cycle_number,
            built_at=world.built_at,
            active_goals_count=len(world.active_goals),
            goals_at_risk_count=len(world.goals_at_risk),
            current_psi=world.current_psi,
            current_flow_mode=world.current_flow_mode,
            pending_bridge_messages=world.pending_bridge_messages,
            opportunities_detected=opportunities_detected,
            opportunities_actioned=opportunities_actioned,
            cycle_duration_ms=duration_ms,
        )
        with Session(self.db_engine) as session:
            session.add(snapshot)
            session.commit()

    def _prune_old_snapshots(self) -> None:
        """Remove world model snapshots older than retention period."""
        cutoff = time.time() - (PCL_SNAPSHOT_RETENTION_HOURS * 3600)
        with Session(self.db_engine) as session:
            old = session.exec(
                select(PCLWorldModelSnapshot).where(PCLWorldModelSnapshot.built_at < cutoff)
            ).all()
            for s in old:
                session.delete(s)
            session.commit()

    # ─── Full Cycle ───────────────────────────────────────────────────────────

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Execute one complete PCL cycle: OBSERVE → MODEL → DETECT → JUDGE → ACT.
        Returns a summary dict for observability.
        Called by the loop and also directly by the API for manual triggering.
        """
        cycle_start = time.time()
        logger.info(f"[PCL] ═══ Cycle {self._cycle_number + 1} ═══")

        # Stage 1+2: Observe + Model
        world = await self.build_world_model()
        logger.info(
            f"[PCL] World model: goals={len(world.active_goals)}, "
            f"at_risk={len(world.goals_at_risk)}, "
            f"psi={world.current_psi:.2f}, "
            f"flow={world.current_flow_mode}, "
            f"bridge_pending={world.pending_bridge_messages}"
        )

        # Stage 3: Detect
        opportunities = self.detect_opportunities(world)
        logger.info(f"[PCL] Detected {len(opportunities)} opportunities")

        # Stage 4: Judge
        approved = self.judge_opportunities(opportunities, world)
        logger.info(f"[PCL] Approved {len(approved)}/{len(opportunities)} opportunities")

        # Stage 5: Act
        actioned = await self.act_on_opportunities(approved, world)

        # Persist snapshot and prune old data
        duration_ms = (time.time() - cycle_start) * 1000
        self._persist_world_snapshot(world, len(opportunities), actioned, duration_ms)

        # Prune old snapshots every 10 cycles
        if self._cycle_number % 10 == 0:
            self._prune_old_snapshots()

        # Broadcast cycle summary to WebSocket
        if self.ws_gateway:
            try:
                asyncio.create_task(self.ws_gateway.broadcast_event("pcl.cycle_complete", {
                    "cycle": self._cycle_number,
                    "opportunities_detected": len(opportunities),
                    "opportunities_actioned": actioned,
                    "flow_mode": world.current_flow_mode,
                    "psi": round(world.current_psi, 3),
                    "duration_ms": round(duration_ms, 1),
                }))
            except Exception as e:
                logger.debug(f"[PCL] WS broadcast failed: {e}")

        summary = {
            "cycle": self._cycle_number,
            "opportunities_detected": len(opportunities),
            "opportunities_actioned": actioned,
            "flow_mode": world.current_flow_mode,
            "psi": world.current_psi,
            "duration_ms": round(duration_ms, 1),
        }
        logger.info(f"[PCL] Cycle complete: {summary}")
        return summary

    # ─── Introspection ────────────────────────────────────────────────────────

    async def get_status(self) -> Dict[str, Any]:
        """Returns current PCL status for the /system/pcl/status endpoint."""
        with Session(self.db_engine) as session:
            recent_opps = session.exec(
                select(PCLOpportunity)
                .order_by(col(PCLOpportunity.detected_at).desc())
                .limit(10)
            ).all()

            recent_snapshots = session.exec(
                select(PCLWorldModelSnapshot)
                .order_by(col(PCLWorldModelSnapshot.built_at).desc())
                .limit(5)
            ).all()

        return {
            "running": self._running,
            "cycle_number": self._cycle_number,
            "cycle_interval_seconds": self.cycle_interval,
            "detectors": [d.name for d in self.detectors],
            "recent_opportunities": [
                {
                    "id": o.id,
                    "title": o.title,
                    "detector": o.detector_name,
                    "priority": o.priority,
                    "outcome": o.outcome,
                    "detected_at": o.detected_at,
                }
                for o in recent_opps
            ],
            "recent_cycles": [
                {
                    "cycle": s.cycle_number,
                    "flow_mode": s.current_flow_mode,
                    "psi": s.current_psi,
                    "opportunities_detected": s.opportunities_detected,
                    "opportunities_actioned": s.opportunities_actioned,
                    "duration_ms": s.cycle_duration_ms,
                }
                for s in recent_snapshots
            ],
        }
