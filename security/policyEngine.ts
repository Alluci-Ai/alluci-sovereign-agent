
import { AutonomyLevel, AceStateVector, ExecutionManifest } from '../kernel/types';

/**
 * [ AUTONOMY_POLICY_ENGINE ]
 * Decides whether an action is permitted based on:
 * 1. The declared AutonomyLevel in the manifest.
 * 2. The Risk Score calculated by the Critic.
 * 3. The current biological/affective state of the user (ACE).
 */
export class AutonomyPolicyEngine {
  
  evaluate(
    manifest: ExecutionManifest,
    riskScore: number, // 0 - 100
    aceState: AceStateVector
  ): boolean {
    
    // 1. Absolute Limits per Level
    if (manifest.autonomyLevel === AutonomyLevel.RESTRICTED) {
      // Restricted execution is extremely conservative.
      if (riskScore > 10) {
        console.warn(`[ POLICY ]: REJECTED. RESTRICTED mode limit (10) exceeded by risk ${riskScore}.`);
        return false;
      }
    }

    // 2. ACE Signal Modulation
    // If the user has low physical energy, the system becomes more conservative (lower threshold).
    // If the user has high cognitive load, the system becomes more conservative to avoid overwhelming them.
    
    const energyModulator = Math.max(0.2, aceState.physicalEnergy); // Floor at 0.2
    const loadModulator = Math.max(0.2, 1.0 - aceState.cognitiveLoad); // Invert load
    
    // Determine Base Threshold
    let baseThreshold = 10;
    switch (manifest.autonomyLevel) {
      case AutonomyLevel.SEMI_AUTONOMOUS:
        baseThreshold = 50;
        break;
      case AutonomyLevel.SOVEREIGN:
        baseThreshold = 90;
        break;
    }

    // Calculate Dynamic Threshold
    // dynamic = base * energy * (1 - load)
    // Example: Sovereign (90) * Low Energy (0.3) * High Load (0.2) = 5.4 (Effectively Restricted)
    const dynamicThreshold = baseThreshold * energyModulator * loadModulator;

    if (riskScore > dynamicThreshold) {
      console.warn(`[ POLICY ]: REJECTED. Risk ${riskScore} exceeds dynamic threshold ${dynamicThreshold.toFixed(2)}.`);
      console.warn(`Details: Base=${baseThreshold}, Energy=${energyModulator.toFixed(2)}, LoadInv=${loadModulator.toFixed(2)}`);
      return false;
    }

    console.info(`[ POLICY ]: APPROVED. Risk ${riskScore} within threshold ${dynamicThreshold.toFixed(2)}.`);
    return true;
  }
}
