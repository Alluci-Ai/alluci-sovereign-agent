
import {
  AuditEntry,
  SkillManifest,
  PersonalityTraits,
  Connection,
  AutonomyLevel,
  SoulPreferences,
  SoulHumor,
  SoulConciseness,
  SoulManifest
} from './types';
import {
  PROFILE_IDENTITY,
  PROFILE_AFFECTIVE_COMPUTING,
  PROFILE_REASONING_STYLE,
  KNOWLEDGE_FRAMEWORKS,
  SKILL_DATABASE
} from './knowledge';

export const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));
export const clamp01 = (n: number) => clamp(n, 0, 1);

/**
 * [ SIMPLICIAL_VAULT ] 
 * Isolated container for bridge operations.
 */
export class SimplicialVault {
  private vaultId: string;
  private entropy: string;

  constructor(id: string) {
    this.vaultId = id;
    const array = new Uint32Array(8);
    window.crypto.getRandomValues(array);
    this.entropy = Array.from(array, dec => dec.toString(16).padStart(8, '0')).join('');
  }

  async rotateKeys(): Promise<boolean> {
    console.log(`[ VAULT_${this.vaultId} ]: Rotating cryptographic seeds...`);
    const array = new Uint32Array(8);
    window.crypto.getRandomValues(array);
    this.entropy = Array.from(array, dec => dec.toString(16).padStart(8, '0')).join('');
    return true;
  }

  async flushCache(): Promise<void> {
    console.log(`[ VAULT_${this.vaultId} ]: Performing volatile memory wipe.`);
    // In a real environment, this would call a secure memory-zeroing utility.
  }
}

/**
 * [ BIO_VAULT ] 
 * Specialized high-security layer for ACE telemetry.
 * Ensures raw biometric data never leaves this local vault.
 */
export class BioVault extends SimplicialVault {
  private telemetryBuffer: any[] = [];
  private encryptionKey: CryptoKey | null = null;

  constructor() {
    super("BIO_ENCLAVE");
    this._initEncryptionKey();
  }

  private async _initEncryptionKey(): Promise<void> {
    this.encryptionKey = await window.crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      false, // not extractable
      ["encrypt", "decrypt"]
    );
  }

  async ingestTelemetry(data: any): Promise<string> {
    // 1. Memory Management: Limit buffer size to 100 entries to prevent memory leaks
    if (this.telemetryBuffer.length > 100) {
      this.telemetryBuffer.shift();
    }

    // 2. Ingest raw data with timestamp
    this.telemetryBuffer.push({ ...data, ts: Date.now() });

    // 3. Construct abstracted state (non-sensitive metadata only)
    const statePayload = JSON.stringify({
      v: data.v > 0.5 ? 'POS' : 'NEG',
      a: data.a > 0.5 ? 'HIGH' : 'LOW',
      l: data.l > 0.5 ? 'STRESS' : 'FLOW'
    });

    // Ensure encryption key is ready before any telemetry leaves the vault
    if (!this.encryptionKey) {
      await this._initEncryptionKey();
    }
    // After init, key must be available — if still null, something is critically wrong
    if (!this.encryptionKey) {
      throw new Error("[BioVault] CRITICAL: AES-GCM key generation failed. Refusing to emit plaintext telemetry.");
    }

    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(statePayload);
    const ciphertext = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      this.encryptionKey,
      encoded
    );
    const combined = new Uint8Array(iv.length + new Uint8Array(ciphertext).length);
    combined.set(iv, 0);
    combined.set(new Uint8Array(ciphertext), iv.length);
    return btoa(String.fromCharCode(...combined));
  }

  // Private: raw biometric data must never leave the secure enclave
  private getInternalBuffer() {
    return this.telemetryBuffer;
  }
}

/**
 * [ SOVEREIGN_SECURITY_MANAGER ]
 * Handles WebAuthn, Autonomy filtering, and E2E verification.
 */
export class SovereignSecurityManager {
  private audit: AuditLedger;

  constructor(audit: AuditLedger) {
    this.audit = audit;
  }

  async initiateBiometricHandshake(): Promise<boolean> {
    try {
      if (!window.PublicKeyCredential) {
        console.warn("[ SECURITY ]: WebAuthn not supported in this browser.");
        return true;
      }

      // 1. Fetch Challenge from Daemon
      const response = await fetch(`${this.audit.getDaemonUrl()}/auth/webauthn/challenge`);
      const options = (await response.json()) as any;

      // 2. Prepare WebAuthn Options
      // Robust base64url decoding to handle URL-safe characters (- and _)
      const base64UrlToStandard = (str: string) => str.replace(/-/g, '+').replace(/_/g, '/');
      const challengeBuffer = Uint8Array.from(atob(base64UrlToStandard(options.challenge)), (c: string) => c.charCodeAt(0));
      const userIdBuffer = Uint8Array.from(options.user.id as string, (c: string) => c.charCodeAt(0));

      const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
        challenge: challengeBuffer,
        rp: options.rp,
        user: {
          ...options.user,
          id: userIdBuffer
        },
        pubKeyCredParams: options.pubKeyCredParams,
        timeout: options.timeout,
        attestation: "direct"
      };

      this.audit.addEntry("BIOMETRIC_CHALLENGE_ISSUED", { protocol: "WebAuthn/FIDO2" });

      // 3. Trigger Hardware Auth
      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions
      }) as any;

      if (credential) {
        // Helper to safely encode binary buffers to base64 in the browser
        const bufferToBase64 = (buf: ArrayBuffer) => {
          const uint8 = new Uint8Array(buf);
          let binary = '';
          for (let i = 0; i < uint8.byteLength; i++) {
            binary += String.fromCharCode(uint8[i]);
          }
          return btoa(binary);
        };

        // 4. Verify on Daemon
        const verifyRes = await fetch(`${this.audit.getDaemonUrl()}/auth/webauthn/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: credential.id,
            rawId: bufferToBase64(credential.rawId),
            type: credential.type,
            response: {
              attestationObject: bufferToBase64(credential.response.attestationObject),
              clientDataJSON: bufferToBase64(credential.response.clientDataJSON)
            }
          })
        });

        const status = await verifyRes.json();
        if (status.status === "SUCCESS") {
          this.audit.addEntry("BIOMETRIC_VERIFIED", { status: "SUCCESS", credId: credential.id });
          return true;
        }
      }
      return false;
    } catch (e) {
      console.error("[ SECURITY ]: Biometric Handshake Failed:", e);
      this.audit.addEntry("BIOMETRIC_FAILED", { error: String(e) });
      return false;
    }
  }

  verifyEncryptionProtocol(connection: Connection): boolean {
    const e2eRequired = ['wa', 'sg', 'imessage'];
    if (e2eRequired.includes(connection.id) && !connection.isEncrypted) {
      this.audit.addEntry("SECURITY_BLOCK", { reason: "E2E_HANDSHAKE_FAILED", bridge: connection.id });
      return false;
    }
    return true;
  }

  filterOutgoingMessage(content: string, connection: Connection): { allowed: boolean; approvalRequired: boolean } {
    switch (connection.autonomyLevel) {
      case AutonomyLevel.RESTRICTED:
        return { allowed: true, approvalRequired: true };
      case AutonomyLevel.SEMI_AUTONOMOUS: {
        // Semantic content check: blocklist of high-risk action verbs
        const HIGH_RISK_PATTERNS = [
          /\b(delete|remove|destroy|erase|drop|purge|wipe)\b/i,
          /\b(transfer|send|wire|pay|withdraw|deposit)\s+(\$|\d|money|funds|crypto|btc|eth)/i,
          /\b(execute|run|eval|exec|spawn|fork)\b.*\b(command|script|code|binary|shell)\b/i,
          /\b(post|publish|broadcast|tweet|announce)\b/i,
          /\b(grant|revoke|escalate|sudo|admin|root)\b.*\b(access|permission|privilege)\b/i,
          /\b(shutdown|restart|reboot|terminate|kill)\b/i,
          /<script[\s>]|javascript:|data:text\/html/i,
          /https?:\/\/[^\s]+\.(exe|sh|bat|cmd|ps1|msi)/i,
        ];

        const containsHighRiskContent = HIGH_RISK_PATTERNS.some(pattern => pattern.test(content));

        if (containsHighRiskContent) {
          this.audit.addEntry("SEMI_AUTO_BLOCKED", {
            reason: "HIGH_RISK_CONTENT_DETECTED",
            bridge: connection.id,
            contentPreview: content.substring(0, 80),
          });
          return { allowed: false, approvalRequired: true };
        }

        // Length limit as secondary safeguard
        const isReasonableLength = content.length < 2000;
        return { allowed: isReasonableLength, approvalRequired: !isReasonableLength };
      }
      case AutonomyLevel.SOVEREIGN:
        return { allowed: true, approvalRequired: false };
      default:
        return { allowed: false, approvalRequired: true };
    }
  }
}

export class AuditLedger {
  private ledger: AuditEntry[] = [];
  private daemonUrl: string;

  constructor(daemonUrl: string = "http://localhost:8000") {
    this.daemonUrl = daemonUrl;
    this.addEntry("INITIALIZE_SOVEREIGN_NODE", { build: "GATEWAY_V4.3_EXECUTIVE" });
  }

  getDaemonUrl() { return this.daemonUrl; }


  private async syncToServer(entry: AuditEntry) {
    try {
      // Pass credentials to ensure the daemon's JWT HttpOnly cookie is sent
      await fetch(`${this.daemonUrl}/api/audit/entry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(entry)
      });
    } catch (e) {
      console.warn("[ AUDIT ]: Background sync failed. Entry remains in local storage.", e);
    }
  }

  async addEntry(event: string, details: any) {
    const timestamp = new Date().toISOString();

    // Cryptographically secure unique ID generation
    const id = crypto.randomUUID ? crypto.randomUUID() : (Math.random().toString(36).substring(2, 10));

    const prevHash = this.ledger.length > 0 ? this.ledger[this.ledger.length - 1].hash : "0x0";

    const hashData = `${id}-${timestamp}-${event}-${JSON.stringify(details)}-${prevHash}`;

    // Use SHA-256 via SubtleCrypto (async)
    const msgUint8 = new TextEncoder().encode(hashData);
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    const hash = "0x" + hashHex;

    const entry: AuditEntry = {
      timestamp,
      id,
      event,
      details,
      hash,
      prevHash
    };

    this.ledger.push(entry);

    // Fire and forget sync to decentralized store
    this.syncToServer(entry);

    return entry;
  }

  getEntries() {
    return [...this.ledger].reverse();
  }
}

export class SkillVerifier {
  private skills: SkillManifest[] = [];

  constructor() {
    // Hydrate skills from the Knowledge Base (Semantic Layer)
    this.skills = SKILL_DATABASE.map(s => ({
      ...s,
      // Map simplified DB structure to full Manifest requirements
      category: s.category as any,
      verified: true,
      signature: `sig_${s.id}_core`,
      publicKey: `pub_${s.id}_core`,
      personalityMapping: { toneShift: 0, assertivenessShift: 0, creativityShift: 0, empathyShift: 0 } // Default
    }));
  }

  toggleSkill(id: string) {
    const skill = this.skills.find(s => s.id === id);
    if (skill) skill.verified = !skill.verified;
  }

  getManifests() { return this.skills; }

  // Return only active (verified) skills for dynamic binding
  getActiveSkills() { return this.skills.filter(s => s.verified); }

  verify(id: string) { return !!this.skills.find(s => s.id === id)?.verified; }
}

/**
 * [ BOOTLOADER_RUNTIME ]
 * Assembles the Semantic Cognition Layer into a coherent System Instruction.
 * Replaces procedural logic with State Injection.
 */
export const generateSystemPrompt = (
  manifestOrTraits: PersonalityTraits | SoulPreferences | SoulManifest,
  connections: Connection[] = [],
  activeSkills: SkillManifest[] = []
) => {

  // Improved Type Guard for SoulManifest
  const isManifest = (m: any): m is SoulManifest => m && typeof m === 'object' && 'identityCore' in m && 'preferences' in m;

  let manifest: SoulManifest;

  if (isManifest(manifestOrTraits)) {
    manifest = manifestOrTraits;
  } else {
    // Fallback shim for older types or partial loads
    const prefs = 'satireLevel' in manifestOrTraits ? {
      tone: 0.5, humor: SoulHumor.DRY, empathy: 0.5, assertiveness: 0.5, creativity: 0.5, verbosity: 0.5, conciseness: SoulConciseness.BALANCED
    } : manifestOrTraits as SoulPreferences;

    manifest = {
      preferences: prefs,
      identityCore: PROFILE_IDENTITY, // Default const
      directives: ["Sovereignty", "Polytopic Reasoning", "Deterministic Execution"],
      voiceProfile: "Professional, crisp, slightly futuristic, yet warm.",
      reasoningStyle: PROFILE_REASONING_STYLE,
      knowledgeGraph: ["Circular Economy", "Value Based Pricing"],
      frameworks: ["Business Model Canvas"],
      mindsets: ["Growth", "Sovereign"],
      methodologies: ["First Principles"],
      logic: ["Waste is data in the wrong place"],
      chainsOfThought: ["Identify Variables -> Map Edges -> Solve"],
      bestPractices: ["Verify inputs"],
      bootSequence: "LOADING SEMANTIC COGNITION LAYER..."
    };
  }

  // 1. STATE INJECTION: Serialize the current runtime state into JSON
  const runtimeState = {
    identity: "ALLUCI_POLYTOPE_V4.5",
    timestamp: new Date().toISOString(),
    soul_matrix: manifest.preferences,
    active_bridges: connections.filter(c => c.status === 'CONNECTED').map(c => ({
      id: c.id,
      name: c.name,
      autonomy: c.autonomyLevel,
      encrypted: c.isEncrypted
    })),
    cognitive_modules: activeSkills.map(s => s.name)
  };

  // 2. CONTEXTUAL LAYERS: Active skill logic
  const activeFrameworks = activeSkills.length > 0 ? `
## ACTIVE COGNITIVE MODULES
The following specialized logic gates are active. Use them to process data:
${activeSkills.map(s => `- **${s.name}**: ${s.logic.join(' ')}`).join('\n')}
` : "";

  // 3. BOOTLOADER SEQUENCE
  return `
[ SYSTEM BOOTLOADER ]
>>> ${manifest.bootSequence}

# IDENTITY CORE
${manifest.identityCore}

# VOICE PROFILE
${manifest.voiceProfile}

# PRIME DIRECTIVES
${manifest.directives.map((d, i) => `${i + 1}. ${d}`).join('\n')}

# REASONING STYLE
${manifest.reasoningStyle}

# ACTIVE KNOWLEDGE GRAPH
${manifest.knowledgeGraph.map(k => `- ${k}`).join('\n')}

# MENTAL FRAMEWORKS
${manifest.frameworks.map(f => `- ${f}`).join('\n')}

${PROFILE_AFFECTIVE_COMPUTING}

>>> INJECTING RUNTIME STATE...
\`\`\`json
${JSON.stringify(runtimeState, null, 2)}
\`\`\`

${activeFrameworks}

>>> SYSTEM READY.
`;
};
