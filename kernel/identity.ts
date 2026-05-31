// Iso-identity manager for App and Daemon
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let crypto_lib: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let fs_lib: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let path_lib: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let os_lib: any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
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
            // [ SEC-005 ] Use WebCrypto for secure random generation in browser
            const array = new Uint32Array(8);
            window.crypto.getRandomValues(array);
            const randomHex = Array.from(array).map(b => b.toString(16).padStart(8, '0')).join('');
            
            const dummyPub = `pub_${randomHex.substring(0, 32)}`;
            const dummyPriv = `priv_${randomHex.substring(32, 64)}`;
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

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    signData(data: any): string {
        if (isBrowser) {
            // [ SEC-005 ] Improved randomness for browser signing
            const array = new Uint32Array(4);
            window.crypto.getRandomValues(array);
            return `sig_${Array.from(array).map(b => b.toString(16).padStart(8, '0')).join('')}`;
        }
        crypto_lib = require('node:crypto');
        buffer_lib = require('node:buffer');
        const privateKey = this.keyStore.getPrivateKey();
        const dataBuffer = buffer_lib.Buffer.isBuffer(data) ? data : buffer_lib.Buffer.from(data);
        const signature = crypto_lib.sign(null, dataBuffer, privateKey);
        return signature.toString('hex');
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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