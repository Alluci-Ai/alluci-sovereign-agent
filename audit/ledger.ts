
import { IdentityManager } from '../kernel/identity';

// Cross-platform SHA-256: works in browser (Web Crypto API) and Node.js
async function sha256(data: string): Promise<string> {
  if (typeof globalThis.crypto !== 'undefined' && globalThis.crypto.subtle) {
    // Browser / Web Crypto API
    const msgUint8 = new TextEncoder().encode(data);
    const hashBuffer = await globalThis.crypto.subtle.digest('SHA-256', msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  } else {
    // Node.js fallback
    const { createHash } = await import('node:crypto');
    return createHash('sha256').update(data).digest('hex');
  }
}

export interface LedgerEntry {
  executionId: string;
  taskId: string;
  timestamp: string;
  actionHash: string;
  signature: string;
  previousHash: string;
}

/**
 * [ AUDIT_LEDGER ]
 * A cryptographic, append-only log of all sovereign actions.
 * Implements hash(n) = SHA256(hash(n-1) + entry).
 */
export class AuditLedger {
  private identity: IdentityManager;
  private chain: LedgerEntry[] = [];
  // Genesis hash
  private lastHash: string = "0000000000000000000000000000000000000000000000000000000000000000";

  constructor(identity: IdentityManager) {
    this.identity = identity;
  }

  /**
   * Records an action into the ledger.
   * Returns the signed entry.
   */
  async recordEntry(executionId: string, taskId: string, actionPayload: any): Promise<LedgerEntry> {
    const timestamp = new Date().toISOString();

    // Canonicalize payload for hashing
    const actionStr = JSON.stringify(actionPayload);
    const actionHash = await sha256(actionStr);

    // The kernel signs the action itself to prove it authorized it
    const signaturePayload = `${executionId}:${taskId}:${timestamp}:${actionHash}`;
    const signature = this.identity.signData(signaturePayload);

    const entry: LedgerEntry = {
      executionId,
      taskId,
      timestamp,
      actionHash,
      signature,
      previousHash: this.lastHash
    };

    // Update the hash chain
    // We hash the canonical JSON of the entry itself to link it
    const entryString = JSON.stringify(entry);
    this.lastHash = await sha256(this.lastHash + entryString);

    this.chain.push(entry);

    // Addressed TODO: Flush to disk (append-only file in Node, localStorage in Browser)
    try {
      if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        const { appendFileSync, existsSync, mkdirSync } = await import('node:fs');
        const { join } = await import('node:path');
        const { homedir } = await import('node:os');
        const auditDir = join(homedir(), '.polytope', 'audit');
        if (!existsSync(auditDir)) mkdirSync(auditDir, { recursive: true });
        appendFileSync(join(auditDir, 'ledger.jsonl'), JSON.stringify(entry) + '\n');
      } else if (typeof globalThis !== 'undefined' && globalThis.localStorage) {
        const key = 'polytope_audit_ledger';
        const existing = JSON.parse(globalThis.localStorage.getItem(key) || '[]');
        existing.push(entry);
        globalThis.localStorage.setItem(key, JSON.stringify(existing));
      }
    } catch (e) {
      console.warn("[ AUDIT ]: Failed to persist entry to permanent storage:", e);
    }

    return entry;
  }

  getHistory(): LedgerEntry[] {
    return [...this.chain];
  }

  /**
   * Verifies the cryptographic integrity of the entire chain.
   */
  async verifyChain(): Promise<boolean> {
    let prev = "0000000000000000000000000000000000000000000000000000000000000000";

    for (const entry of this.chain) {
      if (entry.previousHash !== prev) {
        console.error(`[ AUDIT ]: Broken chain link at task ${entry.taskId}`);
        return false;
      }

      // Re-calculate the hash that this entry produces
      const entryString = JSON.stringify(entry);
      prev = await sha256(prev + entryString);
    }

    return true;
  }
}
