
export enum AutonomyLevel {
  RESTRICTED = "RESTRICTED",
  SEMI_AUTONOMOUS = "SEMI_AUTONOMOUS",
  SOVEREIGN = "SOVEREIGN"
}

export interface ManifestObjective {
  raw: string;
  objectiveHash: string;
}

export interface ExecutionManifest {
  version: string;
  executionId: string; // UUIDv7
  rootPublicKey: string;
  deviceFingerprint: string;
  createdAt: string; // ISO8601
  expiresAt: string; // ISO8601
  objective: ManifestObjective;
  autonomyLevel: AutonomyLevel;
  vaultScope: string[];
  capabilityScope: string[];
  biometricGate: boolean;
  plannerVersion: string;
  modelVersion: string;
  nonce: string;
}

export interface SignedExecutionManifest {
  manifest: ExecutionManifest;
  signature: string; // Hex string (Ed25519)
}

export interface AceStateVector {
  physicalEnergy: number; // 0.0 - 1.0
  emotionalValence: number; // 0.0 - 1.0
  cognitiveLoad: number; // 0.0 - 1.0
}
