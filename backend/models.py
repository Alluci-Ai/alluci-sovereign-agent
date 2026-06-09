# Modified TaskStatus enum and added QueuedTask model

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, ClassVar
from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
import uuid
from sqlalchemy import Enum as SAEnum

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
    checkpoint: Optional[dict] = Field(default=None, sa_column=Column(JSON), default_factory=lambda: None)
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON), default_factory=lambda: None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Note: Existing TaskRecord model remains for run‑specific tasks.

# --- Added model stubs for missing imports ---

# TelemetryData: lightweight pydantic model used by telemetry router and tests
class TelemetryData(BaseModel):
    hr: Optional[int] = None
    hrv: Optional[int] = None
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

# End of added stubs
