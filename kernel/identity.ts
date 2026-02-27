import { generateKeyPairSync, sign, verify, createPublicKey, KeyObject } from 'node:crypto';
import { readFileSync, writeFileSync, existsSync, mkdirSync, chmodSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { Buffer } from 'node:buffer';

/**
 * [ KEY_STORE_ABSTRACTION ]
 * Manages the persistence of the Root Identity (Ed25519).
 * In production, this must interface with the system keychain or HSM.
 */
export class KeyStore {
  private static readonly KEY_DIR = join(homedir(), '.polytope', 'identity');
  private static readonly PRIVATE_KEY_PATH = join(KeyStore.KEY_DIR, 'root.pem');
  private static readonly PUBLIC_KEY_PATH = join(KeyStore.KEY_DIR, 'root.pub');

  constructor() {
    if (!existsSync(KeyStore.KEY_DIR)) {
      mkdirSync(KeyStore.KEY_DIR, { recursive: true, mode: 0o700 });
    } else {
      // Ensure strict permissions on existing directory
      try {
        chmodSync(KeyStore.KEY_DIR, 0o700);
      } catch (error) {
        // Ignore errors on non-POSIX systems or ownership issues
      }
    }
  }

  /**
   * Ensures a valid identity exists. Generates one if missing.
   */
  ensureIdentity(): { publicKey: string } {
    if (!existsSync(KeyStore.PRIVATE_KEY_PATH) || !existsSync(KeyStore.PUBLIC_KEY_PATH)) {
      return this.rotateIdentity();
    }
    const pubKey = readFileSync(KeyStore.PUBLIC_KEY_PATH, 'utf-8');
    return { publicKey: pubKey };
  }

  /**
   * Generates a fresh Ed25519 keypair.
   */
  rotateIdentity(): { publicKey: string } {
    const { privateKey, publicKey } = generateKeyPairSync('ed25519', {
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
    });

    // Write private key with strict 600 permissions (Owner Read/Write only)
    writeFileSync(KeyStore.PRIVATE_KEY_PATH, privateKey as string, { mode: 0o600 });
    
    // Write public key with 644 permissions (Public Read)
    writeFileSync(KeyStore.PUBLIC_KEY_PATH, publicKey as string, { mode: 0o644 });

    return { publicKey: publicKey as string };
  }

  getPrivateKey(): string {
    if (!existsSync(KeyStore.PRIVATE_KEY_PATH)) throw new Error("[ FATAL ]: Identity keystore empty.");
    return readFileSync(KeyStore.PRIVATE_KEY_PATH, 'utf-8');
  }

  getPublicKey(): string {
     if (!existsSync(KeyStore.PUBLIC_KEY_PATH)) throw new Error("[ FATAL ]: Identity keystore empty.");
     return readFileSync(KeyStore.PUBLIC_KEY_PATH, 'utf-8');
  }
}

/**
 * [ IDENTITY_MANAGER ]
 * The Sovereign Authority for signing Execution Manifests.
 */
export class IdentityManager {
  private keyStore: KeyStore;

  constructor() {
    this.keyStore = new KeyStore();
    this.keyStore.ensureIdentity();
  }

  /**
   * Signs a data buffer using the root private key.
   */
  signData(data: Buffer | string): string {
    const privateKey = this.keyStore.getPrivateKey();
    const dataBuffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
    const signature = sign(null, dataBuffer, privateKey);
    return signature.toString('hex');
  }

  /**
   * Verifies a signature against a provided public key.
   */
  verifySignature(data: Buffer | string, signatureHex: string, publicKeyPem: string): boolean {
    try {
      const dataBuffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
      const signature = Buffer.from(signatureHex, 'hex');
      const publicKey = createPublicKey(publicKeyPem);
      return verify(null, dataBuffer, publicKey, signature);
    } catch (e) {
      console.error("[ IDENTITY ]: Verification failed:", e);
      return false;
    }
  }

  getRootPublicKey(): string {
    return this.keyStore.getPublicKey();
  }
}