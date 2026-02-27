
import { createHash, randomUUID } from 'node:crypto';
import { IdentityManager } from './identity';
import { AutonomyLevel, ExecutionManifest, ManifestObjective, SignedExecutionManifest } from './types';

/**
 * [ EXECUTION_MANIFEST_FACTORY ]
 * Generates the immutable contract for a sovereign action.
 * Ensures objective hashing and canonical signing.
 */
export class ExecutionManifestFactory {
  private identity: IdentityManager;
  private readonly PLANNER_VERSION = "4.3.0";
  private readonly MODEL_VERSION = "gemini-pro-1.5";
  private readonly MANIFEST_VERSION = "1.0.0";

  constructor(identity: IdentityManager) {
    this.identity = identity;
  }

  /**
   * Creates a signed manifest.
   * This is the "Intent" that becomes an "Instruction".
   */
  create(
    objectiveRaw: string,
    autonomyLevel: AutonomyLevel,
    vaultScope: string[],
    capabilityScope: string[],
    biometricGate: boolean = false
  ): SignedExecutionManifest {
    
    const now = new Date();
    // Manifests are short-lived by default to prevent replay attacks
    const expires = new Date(now.getTime() + 1000 * 60 * 15); // 15 min expiry

    const objective: ManifestObjective = {
      raw: objectiveRaw,
      objectiveHash: this.hashString(objectiveRaw)
    };

    const manifest: ExecutionManifest = {
      version: this.MANIFEST_VERSION,
      executionId: randomUUID(), // Uses Node's crypto.randomUUID (v4) as execution ID
      rootPublicKey: this.identity.getRootPublicKey(),
      deviceFingerprint: this.getDeviceFingerprint(),
      createdAt: now.toISOString(),
      expiresAt: expires.toISOString(),
      objective,
      autonomyLevel,
      vaultScope,
      capabilityScope,
      biometricGate,
      plannerVersion: this.PLANNER_VERSION,
      modelVersion: this.MODEL_VERSION,
      nonce: randomUUID()
    };

    const canonicalString = this.canonicalize(manifest);
    const signature = this.identity.signData(canonicalString);

    return {
      manifest,
      signature
    };
  }

  /**
   * Validates the integrity and authenticity of a manifest.
   */
  validate(signedManifest: SignedExecutionManifest): boolean {
    const { manifest, signature } = signedManifest;
    
    // 1. Validate Expiration
    if (new Date(manifest.expiresAt) < new Date()) {
      console.warn(`[ MANIFEST ]: Expired at ${manifest.expiresAt}`);
      return false;
    }

    // 2. Validate Objective Integrity
    const currentObjectiveHash = this.hashString(manifest.objective.raw);
    if (currentObjectiveHash !== manifest.objective.objectiveHash) {
      console.error("[ MANIFEST ]: Objective hash mismatch. Possible tampering.");
      return false;
    }

    // 3. Verify Signature against Root Key
    const canonicalString = this.canonicalize(manifest);
    const isValid = this.identity.verifySignature(canonicalString, signature, manifest.rootPublicKey);
    
    if (!isValid) {
      console.error("[ MANIFEST ]: Invalid signature.");
    }

    return isValid;
  }

  private hashString(input: string): string {
    return createHash('sha256').update(input).digest('hex');
  }

  /**
   * Deterministic JSON stringify for signing.
   * Sorts object keys recursively.
   */
  private canonicalize(obj: any): string {
    if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
      return JSON.stringify(obj);
    }
    const sortedKeys = Object.keys(obj).sort();
    const parts = sortedKeys.map(key => {
      return `"${key}":${this.canonicalize(obj[key])}`;
    });
    return `{${parts.join(',')}}`;
  }

  private getDeviceFingerprint(): string {
    // In a real implementation, this checks hardware serials.
    return process.env.DEVICE_FINGERPRINT || "DEV_FINGERPRINT_STUB_NODE_20";
  }
}
