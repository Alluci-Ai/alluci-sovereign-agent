# Modified TaskStatus enum and added QueuedTask model

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Column, JSON, Relationship
import uuid
from sqlalchemy import Enum as SAEnum
import time

# --- Task Models ---

class TaskPriority(Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TaskItem(BaseModel):
    """Immutable task representation used by TaskManager."""
    index: int
    raw_line: str
    description: str
    completed: bool
    priority: TaskPriority
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    """Mutable task data for creating/updating tasks."""
    description: str
    completed: bool = False
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[str] = None


# --- Enums ---
class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"
    SUSPENDED_SECURITY = "suspended_security"

class CognitiveCategory(str, Enum):
    FRAMEWORK = "FRAMEWORK"
    MINDSET = "MINDSET"
    KNOWLEDGE = "KNOWLEDGE"

class ExtrinsicCategory(str, Enum):
    BRIDGE = "BRIDGE"
    MCP = "MCP"
    TOOL = "TOOL"

class RunStatus(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

# --- Existing models (unchanged) ---
# ... (omitted for brevity) ...

# --- New Persistent Queue Model ---
class QueuedTask(SQLModel, table=True):
    __tablename__ = "queued_task"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    status: TaskStatus = Field(default=TaskStatus.QUEUED, sa_column=Column(SAEnum(TaskStatus)))
    payload: dict = Field(sa_column=Column(JSON), default_factory=dict)
    checkpoint: Optional[dict] = Field(sa_column=Column(JSON), default_factory=lambda: None)
    result: Optional[dict] = Field(sa_column=Column(JSON), default_factory=lambda: None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Note: Existing TaskRecord model remains for run‑specific tasks.

# --- Added model stubs for missing imports ---

# TelemetryData: lightweight pydantic model used by telemetry router and tests
class TelemetryData(BaseModel):
    hr: Optional[int] = None
    hrv: Optional[int] = None
    gsr: Optional[float] = None
    respiratory_rate: Optional[int] = None
    stress_score: Optional[float] = None
    valence: Optional[float] = None
    arousal: Optional[float] = None
    focus: Optional[float] = None
    device_id: Optional[str] = None
    sleep_efficiency: Optional[float] = None
    # allow extra fields for future extensions
    class Config:
        extra = "allow"

# AuditEntry: simple audit record for logging events
class AuditEntry(SQLModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: str
    details: str = ""
    status: str = "INFO"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# AuditLog: represents persisted audit logs used by ledger and verifier
class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    event_id: str = Field(index=True)
    verus_txid: Optional[str] = Field(default=None, index=True)
    status: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    integrity_hash: Optional[str] = Field(default=None)
    vdxf_key: Optional[str] = Field(default=None, index=True)
    anchored_timestamp: Optional[datetime] = Field(default=None)
    data: dict = Field(sa_column=Column(JSON), default_factory=dict)

# AgentChannelSubscription: minimal stub for channel subscription model
class AgentChannelSubscription(SQLModel, table=True):
    __tablename__ = "agent_channel_subscription"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str = Field(index=True)
    channel_id: str = Field(index=True)
    subscribed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentSkillBinding(SQLModel, table=True):
    __tablename__ = "agent_skill_binding"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str = Field(index=True)
    skill_id: str = Field(index=True)
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- HLSM Memory Models ---
class HLSMEpisodicEntry(SQLModel, table=True):
    __tablename__ = "hlsm_episodic"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content: str = Field()
    source: str = Field(default="task_result")
    session_key: str = Field(default="")
    objective_hash: str = Field(default="")
    psi_at_encoding: float = Field(default=0.0)
    valence_at_encoding: float = Field(default=0.5)
    topological_importance: float = Field(default=1.0)
    betti_1_support: float = Field(default=0.0)
    access_count: int = Field(default=0)
    last_accessed: float = Field(default_factory=lambda: time.time())
    created_at: float = Field(default_factory=lambda: time.time())
    retention_score: float = Field(default=1.0)
    promoted_to_l2: bool = Field(default=False)
    extra_metadata: Optional[dict] = Field(sa_column=Column(JSON), default=None)

class HLSMWorkingEntry(SQLModel, table=True):
    __tablename__ = "hlsm_working"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_key: str = Field(index=True)
    content: str = Field()
    source: str = Field(default="conversation")
    created_at: float = Field(default_factory=lambda: time.time())
    expires_at: float = Field()

# --- Device and Binding Models ---

class PresenceBeacon(SQLModel, table=True):
    __tablename__ = "presence_beacon"  # type: ignore
    client_id: str = Field(primary_key=True)
    subject: str = Field(index=True)
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Device(SQLModel, table=True):
    __tablename__ = "device"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    public_key: str = Field(nullable=False)
    fingerprint: str = Field(index=True, nullable=False)
    status: str = Field(default="pending")
    capabilities: dict = Field(sa_column=Column(JSON), default_factory=dict)
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceBinding(SQLModel, table=True):
    __tablename__ = "device_binding"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="device.id")
    agent_id: str = Field(index=True)
    token: str = Field(nullable=False)
    expires_at: datetime = Field(nullable=False)

# --- Models for Goals and PCL ---

class GoalRecord(SQLModel, table=True):
    __tablename__ = "goal_record"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    status: str = Field(index=True)
    priority: str = Field(default="MEDIUM")
    metric_current: float = Field(default=0.0)
    metric_target: Optional[float] = Field(default=None)
    deadline: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

class PCLOpportunity(SQLModel, table=True):
    __tablename__ = "pcl_opportunity"  # type: ignore
    id: str = Field(primary_key=True)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actioned: bool = Field(default=False)
    actioned_at: Optional[datetime] = Field(default=None)
    outcome: str = Field(default="")
    # Additional fields can be added as needed

class PCLWorldModelSnapshot(SQLModel, table=True):
    __tablename__ = "pcl_world_model_snapshot"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    cycle_number: int = Field(default=0)
    built_at: float = Field(default_factory=lambda: time.time())
    active_goals_count: int = Field(default=0)
    goals_at_risk_count: int = Field(default=0)
    current_psi: float = Field(default=0.0)
    current_flow_mode: str = Field(default="STANDARD")
    pending_bridge_messages: int = Field(default=0)
    opportunities_detected: int = Field(default=0)
    opportunities_actioned: int = Field(default=0)
    cycle_duration_ms: float = Field(default=0.0)
    snapshot_data: dict = Field(sa_column=Column(JSON), default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskRecord(SQLModel, table=True):
    __tablename__ = "task_record"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    run_id: Optional[int] = Field(default=None, index=True)
    task_id: Optional[int] = Field(default=None, index=True)
    agent_id: Optional[str] = Field(default=None)
    task_dag_id: Optional[str] = Field(default=None)
    action: Optional[str] = Field(default=None)
    args: Optional[dict] = Field(sa_column=Column(JSON), default_factory=dict)
    status: str = Field(index=True)
    error: Optional[str] = Field(default=None)
    result: Optional[dict] = Field(sa_column=Column(JSON), default_factory=dict)
    end_time: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ModelPricing(SQLModel, table=True):
    __tablename__ = "model_pricing"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    model_id: str = Field(index=True, unique=True)
    input_price_per_1m: float
    output_price_per_1m: float
    cache_read_price: Optional[float] = Field(default=None)
    cache_write_price: Optional[float] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Additional SOP model stub

class SOPRecord(SQLModel, table=True):
    __tablename__ = "sop_record"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    steps: dict = Field(sa_column=Column(JSON), default_factory=dict)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- Models for Execution and Auth ---
class Run(SQLModel, table=True):
    __tablename__ = "run"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    objective: str = Field()
    autonomy_level: str = Field()
    status: RunStatus = Field(default=RunStatus.QUEUED, sa_column=Column(SAEnum(RunStatus)))
    agent_id: str = Field(default="executive")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    score: float = Field(default=0.0)
    feedback: Optional[str] = Field(default=None)
    manifest_signature: Optional[str] = Field(default=None)

class LoginRequest(BaseModel):
    """Payload for authentication login endpoint."""
    key: str

class CronJob(SQLModel, table=True):
    __tablename__ = "cron_job"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    agent_id: str = Field(index=True)
    name: str = Field(default="")
    schedule_type: str = Field(default="")
    schedule_value: str = Field(default="")
    payload: str = Field(default="")
    model_override: Optional[str] = Field(default=None)
    thinking_level: Optional[int] = Field(default=None)
    delivery_channel: Optional[str] = Field(default=None)
    delivery_account_id: Optional[str] = Field(default=None)
    delivery_to: Optional[str] = Field(default=None)
    delivery_mode: Optional[str] = Field(default=None)
    reset_context: bool = Field(default=False)
    enabled: bool = Field(default=True)
    last_run_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    runs: List["CronRun"] = Relationship(back_populates="job")

class CronRun(SQLModel, table=True):
    __tablename__ = "cron_run"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="cron_job.id")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="queued")
    job: CronJob = Relationship(back_populates="runs")

# --- Models for Execution Engine and Session Management ---

class DAGTask(BaseModel):
    """Simplified representation of a task in the execution DAG.
    Fields match those used in tests and core engine logic.
    """
    id: str
    action: str
    args: dict = {}
    dependencies: list[str] = []
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None

class SessionConfig(SQLModel, table=True):
    __tablename__ = "session_config"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    session_key: str = Field(index=True)
    label: Optional[str] = Field(default=None)
    model_override: Optional[str] = Field(default=None)
    thinking_level: Optional[int] = Field(default=None)
    verbose_level: Optional[int] = Field(default=None)
    reasoning_level: Optional[int] = Field(default=None)

class AgentRecord(SQLModel, table=True):
    __tablename__ = "agent_record"  # type: ignore
    id: str = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    status: str = Field(index=True)
    model: str = Field(default="gpt-4o")
    description: Optional[str] = Field(default=None)
    fallback_chain: Optional[str] = Field(default="gemini-flash,claude-haiku")
    pii_override_enabled: bool = Field(default=False)
    system_prompt: Optional[str] = Field(default=None)
    # Optional JSON field for heartbeat orders
    heartbeat_orders: Optional[str] = Field(sa_column=Column(JSON), default=None)
    engine_manifest: Optional[str] = Field(sa_column=Column(JSON), default=None)
    tools_manifest: Optional[str] = Field(sa_column=Column(JSON), default=None)
    skills_manifest: Optional[str] = Field(sa_column=Column(JSON), default=None)
    soul_manifest_override: Optional[str] = Field(sa_column=Column(JSON), default=None)
    soul_profile_id: Optional[str] = Field(default=None, foreign_key="soul_profile_record.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

class HeartbeatOrderRecord(SQLModel, table=True):
    __tablename__ = "heartbeat_order_record"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    agent_id: Optional[str] = Field(default=None, foreign_key="agent_record.id")
    order_id: str = Field(index=True)
    order: Optional[int] = Field(default=None)
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    probe_type: Optional[str] = Field(default=None)
    action_type: Optional[str] = Field(default=None)
    outcome: Optional[str] = Field(default=None)
    detail: Optional[str] = Field(default=None)
    signal_stored: bool = Field(default=False)

# --- Soul Models ---

class SoulProfileRecord(SQLModel, table=True):
    __tablename__ = "soul_profile_record"  # type: ignore
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    manifest: dict = Field(sa_column=Column(JSON), default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SoulPreferences(BaseModel):
    """Placeholder for user preferences related to the soul.
    Extend with actual fields as needed.
    """
    tone: Optional[float] = 0.5
    empathy: Optional[float] = 0.5
    assertiveness: Optional[float] = 0.5
    creativity: Optional[float] = 0.5
    verbosity: Optional[float] = 0.5
    humor: Optional[str] = "dry"
    conciseness: Optional[Any] = "balanced"
    preferences: dict = {}

    model_config = {"extra": "allow"}

class SoulManifest(BaseModel):
    """Placeholder for the soul manifest payload.
    The real implementation includes detailed schema; this stub satisfies imports.
    """
    manifest: dict = {}
    directives: list = []
    preferences: Optional[SoulPreferences] = None
    identityCore: Optional[str] = None
    reasoningStyle: Optional[str] = None
    frameworks: Optional[list] = None
    mindsets: Optional[list] = None
    methodologies: Optional[list] = None
    logic: Optional[list] = None
    chainsOfThought: Optional[list] = None
    bestPractices: Optional[list] = None
    voiceProfile: Optional[str] = None
    knowledgeGraph: Optional[list] = None
    bootSequence: Optional[str] = None
    heartbeat: Optional[str] = None
    executionGraph: Optional[dict] = None
    active_skill_ids: Optional[list] = None
    active_tool_ids: Optional[list] = None

    model_config = {"extra": "allow"}

# --- Wallet Models ---

class CurrencyBalance(BaseModel):
    """Simple representation of a currency balance used by VerusWalletService."""
    currency: str
    amount: float

class WalletDashboard(BaseModel):
    connected: bool = False
    identity: Optional[Dict[str, Any]] = None
    balances: List[CurrencyBalance] = []
    total_vrsc: float = 0.0
    unconfirmed: float = 0.0
    mining: Optional[Dict[str, Any]] = None
    recent_transactions: List[Dict[str, Any]] = []
    blockchain: Optional[Dict[str, Any]] = None
    pbaas_chains: List[str] = []
    timestamp: str

# --- Message Log for Analytics Session Tracking ---

class MessageLog(SQLModel, table=True):
    __tablename__ = "message_log"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    session_key: str = Field(index=True)
    role: str = Field()  # "user", "assistant", "system"
    content: Optional[str] = Field(default=None)
    account_id: Optional[str] = Field(default=None, index=True)
    tool_name: Optional[str] = Field(default=None)
    tool_args: Optional[str] = Field(default=None)
    tool_id: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

