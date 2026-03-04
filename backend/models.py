
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

# --- Enums ---
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class RunStatus(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class SoulHumor(str, Enum):
    DRY = "DRY"
    WITTY = "WITTY"
    PLAYFUL = "PLAYFUL"

class SoulConciseness(str, Enum):
    CONCISE = "CONCISE"
    BALANCED = "BALANCED"
    EXPRESSIVE = "EXPRESSIVE"

# --- Database Models (Persistence) ---

class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    objective: str
    autonomy_level: str = Field(default="SEMI_AUTONOMOUS")
    status: str = Field(default=RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    score: float = 0.0
    feedback: Optional[str] = None
    manifest_signature: Optional[str] = None
    
    tasks: List["TaskRecord"] = Relationship(back_populates="run")

class TaskRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    task_dag_id: str  # The ID from the planner (e.g., "step_1")
    action: str
    args: Dict = Field(default={}, sa_column=Column(JSON))
    status: str = Field(default=TaskStatus.PENDING)
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    run: Optional[Run] = Relationship(back_populates="tasks")

# --- Engine Memory Models (Runtime) ---

class DAGTask(BaseModel):
    id: str
    action: str
    args: Dict[str, Any]
    dependencies: List[str] = []
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    retry_count: int = 0
    logs: List[str] = []
    priority_score: float = 0.0

# --- API Schemas ---

class ObjectiveRequest(BaseModel):
    objective: str
    autonomy_level: str = "SEMI_AUTONOMOUS"

class TelemetryData(BaseModel):
    hr: Optional[int] = None
    hrv: Optional[int] = None
    stress_score: Optional[float] = None
    energy_level: Optional[float] = None
    valence: Optional[float] = 0.5
    arousal: Optional[float] = 0.5
    focus: Optional[float] = 0.5
    respiratory_rate: Optional[float] = None
    sleep_efficiency: Optional[float] = None

class SystemStatus(BaseModel):
    cpu_usage: float
    ram_usage: float
    thermal_status: str
    active_bridges: List[str]
    vault_integrity: bool
    daemon_version: str = "4.5.1"
    harmonic_status: Optional[str] = "Inactive"

class LoginRequest(BaseModel):
    key: str

class TaskItem(BaseModel):
    index: int
    raw_line: str
    description: str
    completed: bool
    priority: TaskPriority
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    description: str
    completed: bool
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[str] = None

class SoulPreferences(BaseModel):
    tone: float = Field(0.5, ge=0.0, le=1.0)
    humor: SoulHumor = SoulHumor.DRY
    empathy: float = Field(0.5, ge=0.0, le=1.0)
    assertiveness: float = Field(0.5, ge=0.0, le=1.0)
    creativity: float = Field(0.5, ge=0.0, le=1.0)
    verbosity: float = Field(0.5, ge=0.0, le=1.0) # Legacy support
    conciseness: SoulConciseness = SoulConciseness.BALANCED

class ExecutionGraph(BaseModel):
    nodes: List[Dict[str, Any]] = [] # {id, x, y}
    edges: List[Dict[str, str]] = [] # {source, target}

class SoulManifest(BaseModel):
    preferences: SoulPreferences
    identityCore: str = "You are Alluci, a Sovereign Executive Assistant operating within a high-dimensional Polytope geometry."
    directives: List[str] = ["Sovereignty", "Polytopic Reasoning", "Deterministic Execution"]
    voiceProfile: str = "Professional, crisp, slightly futuristic, yet warm."
    reasoningStyle: str = "Polytopic Method: Vertex Identification, Edge Mapping, Face Selection, Collapse."
    knowledgeGraph: List[str] = ["Circular Economy", "Value Based Pricing", "Verus Ecosystem"]
    frameworks: List[str] = ["Business Model Canvas", "First Principles"]
    mindsets: List[str] = ["Growth", "Sovereign"]
    bootSequence: str = "LOADING SEMANTIC COGNITION LAYER..."
    heartbeat: str = "- [x] Monitor system vitality and task queues.\n- [x] Scan for anomaly patterns in logs."
    executionGraph: Optional[ExecutionGraph] = None
    
    # Extended Cognition Layer
    methodologies: List[str] = []
    logic: List[str] = []
    chainsOfThought: List[str] = []
    bestPractices: List[str] = []
    
class AuditEntry(BaseModel):
    timestamp: str
    id: str
    event: str
    details: Any
    hash: str
    prevHash: str

