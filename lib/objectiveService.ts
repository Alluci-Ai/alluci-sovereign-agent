// lib/objectiveService.ts — CREATE THIS FILE

import { IdentityManager } from '../kernel/identity';
import { ExecutionManifestFactory } from '../kernel/executionManifest';
import { AutonomyPolicyEngine } from '../security/policyEngine';
import { AutonomyLevel, AceStateVector } from '../kernel/types';
import { getCsrfToken } from '../csrfStore';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

// Singleton instances — initialised once per app session
const identity = new IdentityManager();
const policyEngine = new AutonomyPolicyEngine();

/**
 * Submits a sovereign objective to the backend executor.
 * Signs the objective with an Ed25519 execution manifest and applies
 * client-side ACE policy before sending.
 */
export async function submitObjective(
    objective: string,
    autonomyLevel: AutonomyLevel,
    vaultScope: string[],
    capabilityScope: string[],
    aceState: AceStateVector,
    accessToken: string,
    agentId: string = 'executive',
    riskScore: number = 30,
// eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<any> {

    // 1. Client-side policy gate (mirrors Python backend check)
    const permitted = policyEngine.evaluate(
        // We need a partial manifest for the policy check — use the level only
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        { autonomyLevel } as any,
        riskScore,
        aceState,
    );
    if (!permitted) {
        throw new Error(
            `Objective rejected by local autonomy policy. ` +
            `Risk score ${riskScore} exceeds threshold for ${autonomyLevel} mode ` +
            `given current biometric state.`
        );
    }

    // 2. Create and sign the execution manifest
    // Instantiate factory with current model from store (or Vite env default)
    const activeModel = useStore.getState().selectedSkill?.name ?? import.meta.env.VITE_DEFAULT_MODEL ?? 'gemini-2.0-flash';
    const manifestFactory = new ExecutionManifestFactory(identity, activeModel);

    const signedManifest = await manifestFactory.create(
        objective,
        autonomyLevel,
        vaultScope,
        capabilityScope,
        false // biometricGate — set true if ACE approval is required before execution
    );

    // 3. Encode manifest for transport
    const manifestHeader = btoa(JSON.stringify(signedManifest));

    // 4. Fetch CSRF token
    const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);

    // 5. Submit to backend with signed manifest header
    const res = await fetch(`${DAEMON_URL}/api/v1/objective/execute?agent_id=${agentId}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken || '',
            'X-Execution-Manifest': manifestHeader,
        },
        credentials: 'include',
        body: JSON.stringify({
            objective,
            autonomy_level: autonomyLevel,
        }),
    });

    if (!res.ok) {
        const err = await res.text();
        throw new Error(`Objective execution failed: ${res.status} ${err}`);
    }

    return res.json();
}
