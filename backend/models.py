
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

# --- Usage & Cost Analytics Tables (Sprint 1 — Sovereign Spec §4) ---

class UsageLog(SQLModel, table=True):
    """Per-turn token usage log for cost analytics."""
    __tablename__ = "usage_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    session_key: str = Field(index=True)
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

class ModelPricing(SQLModel, table=True):
    """Per-model pricing table ($ per 1M tokens)."""
    __tablename__ = "model_pricing"
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: str = Field(unique=True, index=True)
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    cache_read_price: float = 0.0
    cache_write_price: float = 0.0

# --- Cron Engine Tables (Sprint 1 — Sovereign Spec §3) ---

class ChannelAccount(SQLModel, table=True):
    """
    Multiple account identities for a single bridge type (e.g. 2 Slack workspaces).
    Sovereign Spec §2.3 - Multi-Entity Routing
    """
    __tablename__ = "channel_account"
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_type: str = Field(index=True) # "slack", "telegram", etc.
    account_label: str
    account_identifier: str = Field(unique=True, index=True) # e.g. Team ID or Phone Number
    credentials: Dict = Field(default={}, sa_column=Column(JSON)) # Encrypted if possible
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CronJob(SQLModel, table=True):
    """Scheduled job definition with delivery routing."""
    __tablename__ = "cron_job"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    schedule_type: str  # "interval", "cron", "run_at"
    schedule_value: str  # minutes (interval), cron expr, or ISO datetime
    payload: Optional[str] = None  # objective text or task description
    model_override: Optional[str] = None
    thinking_level: Optional[str] = None
    delivery_channel: Optional[str] = None
    delivery_account_id: Optional[int] = Field(default=None, foreign_key="channel_account.id")
    delivery_to: Optional[str] = None
    delivery_mode: Optional[str] = "none"  # "announce-summary", "post-transcript", "none"
    reset_context: bool = False
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_run_at: Optional[datetime] = None

class CronRun(SQLModel, table=True):
    """Run history record for a cron job."""
    __tablename__ = "cron_run"
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="cron_job.id", index=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: str = "pending"  # "ok", "error", "skipped"
    delivery_status: Optional[str] = None
    log_text: Optional[str] = None

# --- Exec Approval Policies (Sprint 3 — Sovereign Spec §5.6) ---

class ExecPolicy(SQLModel, table=True):
    """Persistent allow/deny policies for tool execution approval."""
    __tablename__ = "exec_policy"
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_name: str = Field(index=True)
    command_pattern: str  # exact command or "*" for wildcard
    decision: str  # "allow" or "deny"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

# --- Session Config Overrides (Sprint 5 — Sovereign Spec §5.4) ---

class SessionConfig(SQLModel, table=True):
    """Per-session parameter overrides (model, thinking level, etc.)."""
    __tablename__ = "session_config"
    id: Optional[int] = Field(default=None, primary_key=True)
    session_key: str = Field(unique=True, index=True)
    label: Optional[str] = None
    model_override: Optional[str] = None
    thinking_level: Optional[str] = None
    verbose_level: Optional[str] = None
    reasoning_level: Optional[str] = None

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
    mode: str = "standard"  # "standard" or "research"

class TelemetryData(BaseModel):
    hr: Optional[int] = None
    hrv: Optional[int] = None
    gsr: Optional[float] = None  # Galvanic Skin Response (μS)
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
    daemon_version: str = "1.0.0"
    harmonic_status: Optional[str] = "Inactive"
    security_audit: Optional[Dict[str, Any]] = None
    update_available: bool = False
    latest_version: Optional[str] = None

class LoginRequest(BaseModel):
    key: str

class AffectiveState(BaseModel):
    valence: float = 512.0   # 0=pessimistic, 512=neutral, 1024=optimistic
    arousal: float = 0.0     # 0=calm, 1024=maximum arousal
    tension: float = 0.0     # 0=relaxed, 1024=maximum contraction

class PolytopeState(BaseModel):
    signature_hash: int
    vertices_V: int
    edges_E: int
    faces_F: int
    betti: List[float]
    affective_tension_psi: float
    phi_total: int = 0
    coherence: float = 0.0
    budget_used: float = 0.0

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
    preferences: SoulPreferences = SoulPreferences()
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
    
class DiscordGuildMapping(SQLModel, table=True):
    """Mapping of Discord Guilds to preferred routing channels (Sovereign Spec §2.3)."""
    __tablename__ = "discord_guild_mapping"
    id: Optional[int] = Field(default=None, primary_key=True)
    guild_id: str = Field(unique=True, index=True)
    guild_name: Optional[str] = None
    default_channel_id: Optional[str] = None
    enabled: bool = True

class MessageLog(SQLModel, table=True):
    """Full transcript record for sessions (Sovereign Spec §5.1)."""
    __tablename__ = "message_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    session_key: str = Field(index=True)
    role: str  # "user", "assistant", "tool", "system"
    content: Optional[str] = None
    account_id: Optional[str] = Field(default=None, index=True) # Reference to ChannelAccount identifier
    tool_name: Optional[str] = None
    tool_args: Optional[str] = None # JSON string
    tool_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

class SessionLogEntry(BaseModel):
    role: str
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None
    timestamp: str

class AuditEntry(BaseModel):
    timestamp: str
    id: str
    event: str
    details: Any
    status: str = "INFO"
    hash: str = ""
    prevHash: str = ""

class AuditLog(SQLModel, table=True):
    """Immutable, append-only audit log stored in the database."""
    __tablename__ = "audit_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(index=True)          # UUID from AuditEntry
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    event: str = Field(index=True)
    details: str = ""
    status: str = Field(default="INFO")
    integrity_hash: Optional[str] = None       # SHA-256 of previous entry chain

class Device(SQLModel, table=True):
    """Device identity for node authentication (Sovereign Spec §4.3)."""
    __tablename__ = "device"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    public_key: str = Field(unique=True, index=True)
    fingerprint: str = Field(unique=True, index=True)
    status: str = Field(default="pending") # "pending", "approved", "revoked"
    capabilities: Dict = Field(default={}, sa_column=Column(JSON))
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceBinding(SQLModel, table=True):
    """Binding between a device and an agent node/resource."""
    __tablename__ = "device_binding"
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="device.id", index=True)
    agent_id: str = Field(index=True)
    token: str = Field(unique=True)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
class PresenceBeacon(SQLModel, table=True):
    """Real-time presence beacon for administrative instances and nodes."""
    __tablename__ = "presence_beacon"
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(unique=True, index=True)
    subject: str
    data_fields: Dict = Field(default={}, sa_column=Column(JSON))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


# --- Wallet API Schemas (Verus Integration) ---

class WalletSendRequest(BaseModel):
    """Request to send currency."""
    to: str
    amount: float
    currency: str = "VRSC"
    memo: str = ""

class WalletConvertRequest(BaseModel):
    """Request to convert currency via DeFi AMM."""
    amount: float
    from_currency: str
    to_currency: str
    via: Optional[str] = None  # Routing basket currency

class WalletInvoiceRequest(BaseModel):
    """Request to create a VerusPay invoice."""
    amount: float
    currency: str = "VRSC"
    memo: str = ""
    expiry_minutes: int = 60

class WalletMiningStartRequest(BaseModel):
    """Request to start mining or staking."""
    mode: str = "mine"  # "mine" or "stake"
    threads: int = 1
    chains: List[str] = ["VRSC"]

class WalletBridgeSendRequest(BaseModel):
    """Request to bridge currency to Ethereum."""
    amount: float
    currency: str = "VRSC"
    eth_address: str

class WalletIdentityUpdateRequest(BaseModel):
    """Request to update VDXF data on the agent's VerusID."""
    key: str
    value: Any

class CurrencyBalance(BaseModel):
    currency: str
    amount: float
    confirmed: bool = True

class WalletDashboard(BaseModel):
    connected: bool
    identity: Optional[Dict[str, Any]] = None
    balances: List[CurrencyBalance]
    total_vrsc: float
    unconfirmed: float
    mining: Optional[Dict[str, Any]] = None
    recent_transactions: List[Dict[str, Any]]
    blockchain: Optional[Dict[str, Any]] = None
    pbaas_chains: List[str]
    timestamp: str

class WalletNodeStatus(BaseModel):
    active: bool
    pid: Optional[int] = None
    sync: Dict[str, Any]
    directories: Dict[str, str]

class WalletNodeAction(BaseModel):
    action: str  # start, stop, restart, provision
