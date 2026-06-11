# Modified TaskStatus enum and added QueuedTask model

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, ClassVar
from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
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

class RunStatus(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

# --- Existing models (unchanged) ---
# ... (omitted for brevity) ...

# --- New Persistent Queue Model ---
class QueuedTask(SQLModel, table=True):
    __tablename__: ClassVar[str] = "queued_task"
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
    # allow extra fields for future extensions
    class Config:
        extra = "allow"

# AuditEntry: simple audit record for logging events
class AuditEntry(SQLModel, table=True):
    __tablename__: ClassVar[str] = "audit_entry"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    event_id: str = Field(index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict = Field(sa_column=Column(JSON), default_factory=dict)

# AuditLog: represents persisted audit logs used by ledger and verifier
class AuditLog(SQLModel, table=True):
    __tablename__: ClassVar[str] = "audit_log"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    event_id: str = Field(index=True)
    verus_txid: Optional[str] = Field(default=None, index=True)
    status: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict = Field(sa_column=Column(JSON), default_factory=dict)

# AgentChannelSubscription: minimal stub for channel subscription model
class AgentChannelSubscription(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_channel_subscription"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str = Field(index=True)
    channel_id: str = Field(index=True)
    subscribed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- HLSM Memory Models ---
class HLSMEpisodicEntry(SQLModel, table=True):
    __tablename__: ClassVar[str] = "hlsm_episodic"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content: str = Field(sa_column=Column(JSON))
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
    __tablename__: ClassVar[str] = "hlsm_working"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_key: str = Field(index=True)
    content: str = Field()
    source: str = Field(default="conversation")
    created_at: float = Field(default_factory=lambda: time.time())
    expires_at: float = Field()

# --- Device and Binding Models ---

class Device(SQLModel, table=True):
    __tablename__: ClassVar[str] = "device"
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    public_key: str = Field(nullable=False)
    fingerprint: str = Field(index=True, nullable=False)
    status: str = Field(default="pending")
    capabilities: dict = Field(sa_column=Column(JSON), default_factory=dict)
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceBinding(SQLModel, table=True):
    __tablename__: ClassVar[str] = "device_binding"
    id: int = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="device.id")
    agent_id: str = Field(index=True)
    token: str = Field(nullable=False)
    expires_at: datetime = Field(nullable=False)

# --- Additional Model Stubs for Goals and PCL ---

class GoalRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "goal_record"
    id: int = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    status: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PCLOpportunity(SQLModel, table=True):
    __tablename__: ClassVar[str] = "pcl_opportunity"
    id: int = Field(default=None, primary_key=True)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actioned: bool = Field(default=False)
    actioned_at: Optional[datetime] = Field(default=None)
    outcome: str = Field(default="")
    # Additional fields can be added as needed

class PCLWorldModelSnapshot(SQLModel, table=True):
    __tablename__: ClassVar[str] = "pcl_world_model_snapshot"
    id: int = Field(default=None, primary_key=True)
    snapshot_data: dict = Field(sa_column=Column(JSON), default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "task_record"
    id: int = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    status: str = Field(index=True)
    result: Optional[dict] = Field(sa_column=Column(JSON), default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Additional SOP model stub

class SOPRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "sop_record"
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    steps: dict = Field(sa_column=Column(JSON), default_factory=dict)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# End of added stubs
# --- Additional Model Stubs for Execution and Auth ---
class Run(SQLModel, table=True):
    __tablename__: ClassVar[str] = "run"
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
    __tablename__: ClassVar[str] = "cron_job"
    id: int = Field(default=None, primary_key=True)
    agent_id: str = Field(index=True)
    enabled: bool = Field(default=True)
    # Additional fields can be added as needed

class CronRun(SQLModel, table=True):
    __tablename__: ClassVar[str] = "cron_run"
    id: int = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="cron_job.id")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="queued")


# --- Additional Model Stubs for Execution Engine and Session Management ---

class DAGTask(BaseModel):
    """Simplified representation of a task in the execution DAG.
    Fields match those used in tests and core engine logic.
    """
    id: str
    action: str
    args: dict = {}
    dependencies: list[str] = []
    status: str = "PENDING"
    result: Optional[str] = None

class SessionConfig(SQLModel, table=True):
    __tablename__: ClassVar[str] = "session_config"
    id: int = Field(default=None, primary_key=True)
    session_key: str = Field(index=True)
    # Extend with additional config fields as needed

class AgentRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_record"
    id: str = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    status: str = Field(index=True)
    # Optional JSON field for heartbeat orders
    heartbeat_orders: Optional[dict] = Field(sa_column=Column(JSON), default=None)

class HeartbeatOrderRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "heartbeat_order_record"
    id: int = Field(default=None, primary_key=True)
    agent_id: str = Field(foreign_key="agent_record.id")
    order: int = Field()
    # Additional fields can be added as needed

# --- Soul Models (stub) ---

class SoulPreferences(BaseModel):
    """Placeholder for user preferences related to the soul.
    Extend with actual fields as needed.
    """
    preferences: dict = {}

class SoulManifest(BaseModel):
    """Placeholder for the soul manifest payload.
    The real implementation includes detailed schema; this stub satisfies imports.
    """
    manifest: dict = {}
    preferences: Optional[SoulPreferences] = None

# --- Wallet Models (stub) ---

class CurrencyBalance(BaseModel):
    """Simple representation of a currency balance used by VerusWalletService."""
    currency: str
    amount: float

class WalletDashboard(SQLModel, table=True):
    __tablename__: ClassVar[str] = "wallet_dashboard"
    id: int = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    # Store balances as a JSON dict mapping currency to amount for simplicity
    balances: dict = Field(sa_column=Column(JSON), default_factory=dict)
