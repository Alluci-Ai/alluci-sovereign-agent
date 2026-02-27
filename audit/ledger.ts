
import { createHash } from 'node:crypto';
import { IdentityManager } from '../kernel/identity';

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
    const actionHash = createHash('sha256').update(actionStr).digest('hex');

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
    this.lastHash = createHash('sha256').update(this.lastHash + entryString).digest('hex');

    this.chain.push(entry);
    
    // TODO: In Phase 4, flush to disk immediately (append-only file)
    
    return entry;
  }

  getHistory(): LedgerEntry[] {
    return [...this.chain];
  }

  /**
   * Verifies the cryptographic integrity of the entire chain.
   */
  verifyChain(): boolean {
    let prev = "0000000000000000000000000000000000000000000000000000000000000000";
    
    for (const entry of this.chain) {
      if (entry.previousHash !== prev) {
        console.error(`[ AUDIT ]: Broken chain link at task ${entry.taskId}`);
        return false;
      }
      
      // Re-calculate the hash that this entry produces
      const entryString = JSON.stringify(entry);
      prev = createHash('sha256').update(prev + entryString).digest('hex');
    }
    
    return true;
  }
}
