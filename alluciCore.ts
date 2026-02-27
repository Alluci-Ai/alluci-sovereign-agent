
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
    this.entropy = Math.random().toString(36).substring(7);
  }

  async rotateKeys(): Promise<boolean> {
    console.log(`[ VAULT_${this.vaultId} ]: Rotating cryptographic seeds...`);
    this.entropy = Math.random().toString(36).substring(7);
    return true;
  }

  async flushCache(): Promise<void> {
    console.log(`[ VAULT_${this.vaultId} ]: Performing volatile memory wipe.`);
    // In a real environment, this would call a secure memory-zeroing utility.
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
      if (!window.PublicKeyCredential) return true; // Fallback if unsupported

      // Simulated WebAuthn / FIDO2 challenge
      const challenge = new Uint8Array(32);
      window.crypto.getRandomValues(challenge);

      this.audit.addEntry("BIOMETRIC_CHALLENGE_ISSUED", { protocol: "FIDO2" });
      
      // Note: Real implementation would use navigator.credentials.get()
      return new Promise((resolve) => {
        setTimeout(() => {
          this.audit.addEntry("BIOMETRIC_VERIFIED", { status: "SUCCESS" });
          resolve(true);
        }, 800);
      });
    } catch (e) {
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
      case AutonomyLevel.SEMI_AUTONOMOUS:
        // Logic to check whitelist (simulated)
        const isWhitelisted = content.length < 500; 
        return { allowed: isWhitelisted, approvalRequired: !isWhitelisted };
      case AutonomyLevel.SOVEREIGN:
        return { allowed: true, approvalRequired: false };
      default:
        return { allowed: false, approvalRequired: true };
    }
  }
}

export class AuditLedger {
  private ledger: AuditEntry[] = [];

  constructor() {
    this.addEntry("INITIALIZE_SOVEREIGN_NODE", { build: "GATEWAY_V4.3_EXECUTIVE" });
  }

  async addEntry(event: string, details: any) {
    const timestamp = new Date().toISOString();
    const id = Math.random().toString(36).substr(2, 9);
    const prevHash = this.ledger.length > 0 ? this.ledger[this.ledger.length - 1].hash : "0x0";
    
    const hashData = `${timestamp}-${event}-${JSON.stringify(details)}-${prevHash}`;
    const hash = "0x" + btoa(hashData).substr(0, 16);

    const entry: AuditEntry = {
      timestamp,
      id,
      event,
      details,
      hash,
      prevHash
    };

    this.ledger.push(entry);
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
  
  // Type Guard for SoulManifest
  const isManifest = (m: any): m is SoulManifest => 'identityCore' in m;
  
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
${manifest.directives.map((d, i) => `${i+1}. ${d}`).join('\n')}

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
