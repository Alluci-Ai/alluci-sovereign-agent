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
  const getAgentSubscriptions = useCallback(async (agentId: string) => {
    try {
      const state = useStore.getState();
      const token = state.accessToken || localStorage.getItem('alluci_daemon_token');
      const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/subscriptions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return await res.json();
    } catch (error) {
      console.error("Failed to fetch subscriptions:", error);
      return [];
    }
  }, []);

  const updateAgentSubscription = useCallback(async (agentId: string, channelId: string, isActive: boolean) => {
    try {
      const state = useStore.getState();
      const token = state.accessToken || localStorage.getItem('alluci_daemon_token');
      const csrfToken = await getCsrfToken(DAEMON_URL, token || '');
      
      const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/subscriptions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-CSRF-Token': csrfToken || ''
        },
        body: JSON.stringify({ channel_id: channelId, is_active: isActive })
      });
      return await res.json();
    } catch (error) {
      console.error("Failed to update subscription:", error);
      return { status: "ERROR" };
    }
  }, []);

  return { isBusy, executeObjective, getAgentSubscriptions, updateAgentSubscription };
};
