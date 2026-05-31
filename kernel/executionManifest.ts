// kernel/executionManifest.ts — RE-APPLIED FIX
const isBrowser = typeof window !== 'undefined';
let crypto_lib: any;

import { IdentityManager } from './identity';
import {
    AutonomyLevel,
    ExecutionManifest,
    ManifestObjective,
    SignedExecutionManifest,
} from './types';

// ── Version constants ──────────────────────────────────────────────────────────
const APP_VERSION: string =
    (typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : null) ??
    (() => {
        try {
            // eslint-disable-next-line @typescript-eslint/no-var-requires
            return require('../package.json').version as string;
        } catch {
            return '0.0.0-unknown';
        }
    })();

const MANIFEST_VERSION = '1.0.0';

/**
 * [ EXECUTION_MANIFEST_FACTORY ]
 *
 * Generates the immutable, signed contract for a sovereign action.
 * Each manifest binds an objective to an identity, autonomy level,
 * vault scope, capability scope, and the active model version.
 *
 * Model and planner versions are injected at construction time
 * from the active inference configuration — they are NOT hardcoded.
 */
export class ExecutionManifestFactory {
    private identity: IdentityManager;
    private readonly plannerVersion: string;
    private readonly modelVersion: string;

    /**
     * @param identity       - The IdentityManager holding the root Ed25519 keypair.
     * @param modelVersion   - The active model ID (e.g. 'gemini-2.0-flash').
     * @param plannerVersion - The planner version string. Defaults to APP_VERSION.
     */
    constructor(
        identity: IdentityManager,
        modelVersion?: string,
        plannerVersion?: string,
    ) {
        this.identity = identity;
        this.plannerVersion = plannerVersion ?? APP_VERSION;
        this.modelVersion =
            modelVersion ??
            (import.meta?.env?.VITE_DEFAULT_MODEL as string | undefined) ??
            'unknown';
    }

    /**
     * Creates a signed execution manifest.
     */
    async create(
        objectiveRaw: string,
        autonomyLevel: AutonomyLevel,
        vaultScope: string[],
        capabilityScope: string[],
        biometricGate = false,
    ): Promise<SignedExecutionManifest> {
        const now = new Date();
        const expires = new Date(now.getTime() + 1_000 * 60 * 15); // 15-minute expiry

        const objective: ManifestObjective = {
            raw: objectiveRaw,
            objectiveHash: await this.hashString(objectiveRaw),
        };

        const manifest: ExecutionManifest = {
            version: MANIFEST_VERSION,
            executionId: isBrowser ? crypto.randomUUID() : require('node:crypto').randomUUID(),
            rootPublicKey: this.identity.getRootPublicKey(),
            deviceFingerprint: this.getDeviceFingerprint(),
            createdAt: now.toISOString(),
            expiresAt: expires.toISOString(),
            objective,
            autonomyLevel,
            vaultScope,
            capabilityScope,
            biometricGate,
            plannerVersion: this.plannerVersion,
            modelVersion: this.modelVersion,
            nonce: isBrowser ? crypto.randomUUID() : require('node:crypto').randomUUID(),
        };

        const canonicalString = this.canonicalize(manifest);
        const signature = this.identity.signData(canonicalString);

        return { manifest, signature };
    }

    /**
     * Validates the integrity and authenticity of a previously signed manifest.
     */
    async validate(signedManifest: SignedExecutionManifest): Promise<boolean> {
        const { manifest, signature } = signedManifest;

        // 1. Expiry
        if (new Date(manifest.expiresAt) < new Date()) {
            console.warn(`[ MANIFEST ]: Expired at ${manifest.expiresAt}`);
            return false;
        }

        // 2. Objective integrity
        if (await this.hashString(manifest.objective.raw) !== manifest.objective.objectiveHash) {
            console.error('[ MANIFEST ]: Objective hash mismatch. Possible tampering.');
            return false;
        }

        // 3. Signature
        const canonicalString = this.canonicalize(manifest);
        const isValid = this.identity.verifySignature(
            canonicalString,
            signature,
            manifest.rootPublicKey,
        );
        if (!isValid) {
            console.error('[ MANIFEST ]: Invalid signature.');
        }
        return isValid;
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    private async hashString(input: string): Promise<string> {
        if (isBrowser) {
            const encoder = new TextEncoder();
            const data = encoder.encode(input);
            const hashBuffer = await crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        }
        return require('node:crypto').createHash('sha256').update(input).digest('hex');
    }

    /**
     * Deterministic JSON stringify with recursively sorted keys.
     */
    private canonicalize(obj: unknown): string {
        if (obj === null || typeof obj !== 'object') {
            return JSON.stringify(obj);
        }
        if (Array.isArray(obj)) {
            return `[${obj.map(item => this.canonicalize(item)).join(',')}]`;
        }
        const sorted = Object.keys(obj as Record<string, unknown>).sort();
        const parts = sorted.map(key => {
            const val = (obj as Record<string, unknown>)[key];
            return `"${key}":${this.canonicalize(val)}`;
        });
        return `{${parts.join(',')}}`;
    }

    private getDeviceFingerprint(): string {
        if (process.env.DEVICE_FINGERPRINT) return process.env.DEVICE_FINGERPRINT;
        try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const os = require('node:os') as typeof import('node:os');
            const data = `${os.hostname()}-${os.platform()}-${os.arch()}`;
            return require('node:crypto').createHash('sha256').update(data).digest('hex').substring(0, 16).toUpperCase();
        } catch {
            return 'FALLBACK_NODE_ID';
        }
    }
}
