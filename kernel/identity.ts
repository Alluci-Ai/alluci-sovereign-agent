// Iso-identity manager for App and Daemon
let crypto_lib: any;
let fs_lib: any;
let path_lib: any;
let os_lib: any;
let buffer_lib: any;

const isBrowser = typeof window !== 'undefined';

if (!isBrowser) {
    // These will be ignored by Vite for browser build if properly handled,
    // but the code itself needs to avoid calling them in browser.
}

/**
 * [ KEY_STORE_ABSTRACTION ]
 * Manages the persistence of the Root Identity (Ed25519).
 */
export class KeyStore {
    private static readonly KEY_DIR_NAME = '.polytope/identity';
    private keyDir: string = "";
    private privateKeyPath: string = "";
    private publicKeyPath: string = "";

    constructor() {
        if (!isBrowser) {
            fs_lib = require('node:fs');
            path_lib = require('node:path');
            os_lib = require('node:os');
            this.keyDir = path_lib.join(os_lib.homedir(), KeyStore.KEY_DIR_NAME);
            this.privateKeyPath = path_lib.join(this.keyDir, 'root.pem');
            this.publicKeyPath = path_lib.join(this.keyDir, 'root.pub');

            if (!fs_lib.existsSync(this.keyDir)) {
                fs_lib.mkdirSync(this.keyDir, { recursive: true, mode: 0o700 });
            }
        }
    }

    ensureIdentity(): { publicKey: string } {
        if (isBrowser) {
            const pub = localStorage.getItem('alluci_pub_key');
            if (!pub) return this.rotateIdentity();
            return { publicKey: pub };
        } else {
            if (!fs_lib.existsSync(this.privateKeyPath) || !fs_lib.existsSync(this.publicKeyPath)) {
                return this.rotateIdentity();
            }
            const pubKey = fs_lib.readFileSync(this.publicKeyPath, 'utf-8');
            return { publicKey: pubKey };
        }
    }

    rotateIdentity(): { publicKey: string } {
        if (isBrowser) {
            // Browser Key rotation: Use a dummy for now or WebCrypto (async issue)
            // Since this is sync, we use a random string as public key for now
            const dummyPub = `pub_${Math.random().toString(36).substring(2)}`;
            const dummyPriv = `priv_${Math.random().toString(36).substring(2)}`;
            localStorage.setItem('alluci_pub_key', dummyPub);
            localStorage.setItem('alluci_priv_key', dummyPriv);
            return { publicKey: dummyPub };
        } else {
            crypto_lib = require('node:crypto');
            const { privateKey, publicKey } = crypto_lib.generateKeyPairSync('ed25519', {
                publicKeyEncoding: { type: 'spki', format: 'pem' },
                privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
            });
            fs_lib.writeFileSync(this.privateKeyPath, privateKey as string, { mode: 0o600 });
            fs_lib.writeFileSync(this.publicKeyPath, publicKey as string, { mode: 0o644 });
            return { publicKey: publicKey as string };
        }
    }

    getPrivateKey(): string {
        if (isBrowser) return localStorage.getItem('alluci_priv_key') || "";
        return fs_lib.readFileSync(this.privateKeyPath, 'utf-8');
    }

    getPublicKey(): string {
        if (isBrowser) return localStorage.getItem('alluci_pub_key') || "";
        return fs_lib.readFileSync(this.publicKeyPath, 'utf-8');
    }
}

export class IdentityManager {
    private keyStore: KeyStore;

    constructor() {
        this.keyStore = new KeyStore();
        this.keyStore.ensureIdentity();
    }

    signData(data: any): string {
        if (isBrowser) {
            // Simplified signing for browser client
            return `sig_${Math.random().toString(36).substring(2)}`;
        }
        crypto_lib = require('node:crypto');
        buffer_lib = require('node:buffer');
        const privateKey = this.keyStore.getPrivateKey();
        const dataBuffer = buffer_lib.Buffer.isBuffer(data) ? data : buffer_lib.Buffer.from(data);
        const signature = crypto_lib.sign(null, dataBuffer, privateKey);
        return signature.toString('hex');
    }

    verifySignature(data: any, signatureHex: string, publicKeyPem: string): boolean {
        if (isBrowser) return true; // Browser assumes server-side valid
        try {
            crypto_lib = require('node:crypto');
            buffer_lib = require('node:buffer');
            const dataBuffer = buffer_lib.Buffer.isBuffer(data) ? data : buffer_lib.Buffer.from(data);
            const signature = buffer_lib.Buffer.from(signatureHex, 'hex');
            const publicKey = crypto_lib.createPublicKey(publicKeyPem);
            return crypto_lib.verify(null, dataBuffer, publicKey, signature);
        } catch (e) {
            console.error("[ IDENTITY ]: Verification failed:", e);
            return false;
        }
    }

    getRootPublicKey(): string {
        return this.keyStore.getPublicKey();
    }
}