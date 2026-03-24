// usePolytopeAPI.ts — RE-APPLIED FIX

import { useState, useCallback } from 'react';
import { getCsrfToken } from './csrfStore';
import { submitObjective } from './lib/objectiveService';
import { useStore } from './store/useStore';
import { AutonomyLevel, AceStateVector } from './kernel/types';

export const DAEMON_URL = import.meta.env.VITE_DAEMON_URL;

export const usePolytopeAPI = () => {
  const [isBusy, setIsBusy] = useState(false);

  const executeObjective = useCallback(async (objective: string, autonomy: AutonomyLevel = AutonomyLevel.SEMI_AUTONOMOUS) => {
    setIsBusy(true);
    try {
      const state = useStore.getState();
      const token = state.accessToken || localStorage.getItem('alluci_daemon_token');
      if (!token) return "[ ERROR ]: Access Denied. Daemon token missing.";

      const aceState: AceStateVector = {
        physicalEnergy: state.biometrics.physical,
        emotionalValence: state.biometrics.emotional,
        cognitiveLoad: state.biometrics.cognitive,
      };

      const result = await submitObjective(
        objective,
        autonomy,
        [], // vaultScope
        [], // capabilityScope
        aceState,
        token
      );
      
      return result.result;
    } catch (error: any) {
      console.error("Daemon link failure:", error);
      return `[ ERROR ]: ${error.message || "Daemon manifold unreachable."}`;
    } finally {
      setIsBusy(false);
    }
  }, []);

  return { isBusy, executeObjective };
};
