import { GroundingSource, FilePart } from './geminiService';

export interface Message {
  text: string;
  isUser: boolean;
  sources?: GroundingSource[];
  timestamp: string;
  isCompaction?: boolean;
  /** Number of tokens freed during context compaction (populated by WS event) */
  tokenCount?: number;
  /** Name of the model that generated this message */
  modelName?: string;
  /** Message type to separate chat from dispatch logs */
  type?: 'chat' | 'dispatch';
  /** Optional unique ID to support dynamic streaming updates */
  id?: string;
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
  category: 'BRIDGE' | 'MCP' | 'TOOL' | string;
  description: string;
  enabled: boolean;
  params: string;
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