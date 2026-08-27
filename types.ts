import { GroundingSource, FilePart } from './geminiService';

export interface Message {
  text?: string;
  isUser?: boolean;
  sources?: GroundingSource[];
  timestamp?: string;
  isCompaction?: boolean;
  /** Number of tokens freed during context compaction (populated by WS event) */
  tokenCount?: number;
  /** Name of the model that generated this message */
  modelName?: string;
  /** Message type to separate chat from dispatch logs */
  type?: 'chat' | 'dispatch';
  /** Optional unique ID to support dynamic streaming updates */
  id?: string;
  /** Optional role/sender/content for external or legacy session format compatibility */
  sender?: string;
  role?: string;
  content?: string;
}

export interface PendingAttachment extends FilePart {
  name: string;
}

export enum EmotionalState {
  EXCITED = "excited",
  CURIOUS = "curious",
  CONTEMPLATIVE = "contemplative",
  PASSIONATE = "passionate",
  CONCERNED = "concerned",
  PLAYFUL = "playful",
  FOCUSED = "focused",
  EMPATHETIC = "empathetic",
  INSPIRED = "inspired",
  ANALYTICAL = "analytical",
  NURTURING = "nurturing",
  DETERMINED = "determined",
  REFLECTIVE = "reflective",
  VISIONARY = "visionary",
  GROUNDED = "grounded"
}

export enum AutonomyLevel {
  RESTRICTED = "RESTRICTED",
  SEMI_AUTONOMOUS = "SEMI_AUTONOMOUS",
  SOVEREIGN = "SOVEREIGN"
}

export interface AffectiveState {
  valence: number;
  arousal: number;
  tension: number;
}

export interface AuditEntry {
  timestamp: string;
  id: string;
  event: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  details: any;
  hash: string;
  prevHash: string;
}

export interface SkillPersonalityImpact {
  toneShift?: number; // -1.0 to 1.0
  creativityShift?: number;
  assertivenessShift?: number;
  empathyShift?: number;
}

export interface SkillManifest {
  id: string;
  name: string;
  category: 'BRIDGE' | 'MANIFOLD' | 'FRAMEWORK' | 'CUSTOM' | 'MCP' | 'TOOL' | 'KNOWLEDGE' | 'MINDSET' | string;
  description: string;

  // [ COGNITIVE_LAYERS ]
  knowledge: string[];       // Declarative memory blocks
  mindsets: string[];        // Attitudinal stances
  methodologies: string[];   // Procedural templates
  frameworks: string[];      // Structural logic schemas
  chainsOfThought: string[]; // Explicit reasoning steps
  logic: string[];           // Governing axioms (Deductive/Inductive)
  tools?: string[];          // Extrinsic Dependencies (MCPs, APIs, CLIs)
  reference_docs?: string[]; // Documentation or large MD files

  // [ DYNAMIC_BINDING ]
  personalityMapping: SkillPersonalityImpact;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  heartbeat?: any[];

  // [ EXECUTION_INSTRUCTIONS ]
  instructions?: string; // Markdown instructions for the cognitive module

  // [ METADATA_&_SECURITY ]
  signature: string;
  publicKey: string;
  verified: boolean;

  // Legacy support for capability routing
  capabilities: string[];
  bestPractices?: string[];
  voiceProfile?: string;
}

export interface ToolManifest {
  id: string;
  name: string;
  category: 'API' | 'MCP' | 'CLI' | 'RPC' | 'TOOL' | string;
  description: string;
  enabled: boolean;
  
  // Multi-capability Tool Engine
  capabilities?: Record<string, {
    type: string;
    baseUrl?: string;
    endpoint?: string;
    method?: string;
    authType?: string;
    authHeadersVaultId?: string;
    transport?: 'stdio' | 'sse';
    command?: string;
    url?: string;
    envVarsVaultId?: Record<string, string>;
    sandboxed?: boolean;
  }>;

  // Dynamic Execution Routing (Legacy single-capability)
  execution?: {
    type: 'API' | 'MCP' | 'CLI' | 'RPC';
    baseUrl?: string;           // API
    endpoint?: string;          // API
    method?: string;            // API
    authType?: string;          // API/OAuth2
    authHeadersVaultId?: string; // Vault reference ID
    transport?: 'stdio' | 'sse'; // MCP
    command?: string;           // MCP/CLI
    url?: string;               // MCP (SSE)
    envVarsVaultId?: Record<string, string>;     // Vault reference IDs for Environment Variables
    sandboxed?: boolean;        // CLI
  };
  
  // Strict Parameter Validation
  schema?: {
    type: 'object';
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    properties: Record<string, any>;
    required: string[];
  };
  
  // Legacy or simplified params
  params?: string;
  reference_docs?: string[];
  dependencies?: string[];
  verified?: boolean;
  source?: string;
  version?: string;
  author?: string;
  signature?: string;
  last_active?: string;

  // Subsystems mapping
  mcp?: Record<string, any>;
  lsp?: Record<string, any>;
  formatter?: Record<string, any>;
  command?: Record<string, any>;
  references?: Record<string, any>;
  
  // Security PCL (Permission Control List)
  permissions?: string[];
}

export enum SoulHumor {
  DRY = "DRY",
  WITTY = "WITTY",
  PLAYFUL = "PLAYFUL"
}

export enum SoulConciseness {
  CONCISE = "CONCISE",
  BALANCED = "BALANCED",
  EXPRESSIVE = "EXPRESSIVE"
}

export interface SoulPreferences {
  tone: number; // 0 (Casual) - 1 (Formal)
  humor: SoulHumor;
  empathy: number; // 0 (Robotic) - 1 (Compassionate)
  assertiveness: number; // 0 (Passive) - 1 (Commanding)
  creativity: number; // 0 (Deterministic) - 1 (Divergent)
  verbosity: number; // Legacy support, mapped to conciseness
  conciseness: SoulConciseness;
}

export interface GraphNode {
  id: string;
  x: number;
  y: number;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface ExecutionGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SoulManifest {
  preferences: SoulPreferences;
  identityCore: string;
  directives: string[];
  voiceProfile: string;
  reasoningStyle: string;
  knowledgeGraph: string[];
  frameworks: string[];
  mindsets: string[];
  bootSequence: string;
  heartbeat?: string;
  executionGraph?: ExecutionGraph;
  // Extended Cognition
  methodologies: string[];
  logic: string[];
  chainsOfThought: string[];
  bestPractices: string[];
  active_skill_ids?: string[];
  active_tool_ids?: string[];
}

export interface PersonalityTraits {
  satireLevel: number;
  analyticalDepth: number;
  protectiveBias: number;
  verbosity: number;
}

export type AuthType =
  | 'OAUTH2'
  | 'SECURE_TUNNEL'
  | 'IDENTITY_LINK'
  | 'QR_SYNC'
  | 'TOKEN'
  | 'WEB_SESSION'
  | 'VDXF_HANDSHAKE'
  | 'MACOS_PERMS';

export interface HardwareProfile {
  arch: string;
  os: string;
  acceleration: 'METAL' | 'CUDA' | 'ROCM' | 'CPU' | 'NEON' | 'NONE';
  integrity: number;
}

export interface Connection {
  id: string;
  name: string;
  status: 'DISCONNECTED' | 'BINDING' | 'CONNECTED';
  type: 'MESSAGING' | 'WORKSPACE';
  authType: AuthType;
  autonomyLevel: AutonomyLevel;
  accountAlias?: string;
  profileImg?: string;
  lastSynced?: string;
  isEncrypted: boolean;
  vaultId?: string;
  accounts?: any[];
}

export interface ApiManifoldKeys {
  llm: Record<string, string>;
  audio: Record<string, string>;
  music: Record<string, string>;
  image: Record<string, string>;
  video: Record<string, string>;
}

export interface TaskItem {
  index: number;
  description: string;
  completed: boolean;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  due_date: string | null;
}

export interface ModalState {
  settings: boolean;
  drive: boolean;
  audit: boolean;
  preferences: boolean;
  soul: boolean;
  apiManifold: boolean;
  taskPanel: boolean;
  skillWizard: boolean;
  apiWizard: boolean;
}

// --- Artifact Workspace Interfaces ---

export type ArtifactKind =
  | 'code'
  | 'html'
  | 'web'
  | 'presentation'
  | 'pdf'
  | 'image'
  | 'text'
  | 'data';

export type ArtifactStatus =
  | 'draft'
  | 'generating'
  | 'ready'
  | 'updating'
  | 'published'
  | 'failed';

export interface ArtifactPage {
  id: string;
  index: number;
  title: string;
  thumbnailUrl?: string;
  renderUrl?: string;
  html?: string;
}

export interface ArtifactVersion {
  id: string;
  version: number;
  createdBy: string;
  reason?: string;
  createdAt: string;
}

export interface Artifact {
  id: string;
  workspaceId: string;
  ownerId: string;
  kind: ArtifactKind;
  title: string;
  mimeType: string;
  status: ArtifactStatus;
  currentVersion: number;
  sourceUri?: string;
  content?: string;
  pages?: ArtifactPage[];
  metadata: {
    language?: string;
    framework?: string;
    entrypoint?: string;
    width?: number;
    height?: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
  };
  createdAt: string;
  updatedAt: string;
}