import { useState, useCallback } from 'react';
import { getCsrfToken } from './csrfStore';

export const DAEMON_URL = 'http://localhost:8000';

export const usePolytopeAPI = () => {
  const [isBusy, setIsBusy] = useState(false);

  const executeObjective = useCallback(async (objective: string) => {
    setIsBusy(true);
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${DAEMON_URL}/api/v1/objective/execute`, {
        method: 'POST',
        headers: {
          ...headers,
          'X-CSRF-Token': await getCsrfToken(DAEMON_URL, token) || ''
        },
        body: JSON.stringify({ objective }),
      });
      
      if (response.status === 401) {
        return "[ ERROR ]: Access Denied. Daemon token invalid or expired.";
      }
      
      const data = await response.json();
      return data.result;
    } catch (error) {
      console.error("Daemon link failure:", error);
      return "[ ERROR ]: Daemon manifold unreachable.";
    } finally {
      setIsBusy(false);
    }
  }, []);

  const getAgentSubscriptions = useCallback(async (agentId: string) => {
    try {
      const response = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/subscriptions`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('alluci_daemon_token')}` }
      });
      return await response.json();
    } catch (err) {
      console.error("Failed to fetch subscriptions:", err);
      return [];
    }
  }, []);

  const updateAgentSubscription = useCallback(async (agentId: string, channelId: string, isActive: boolean) => {
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const response = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/subscriptions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-CSRF-Token': await getCsrfToken(DAEMON_URL, token) || ''
        },
        body: JSON.stringify({ channel_id: channelId, is_active: isActive }),
      });
      return await response.json();
    } catch (err) {
      console.error("Failed to update subscription:", err);
      return { status: "ERROR" };
    }
  }, []);

  const deleteAgentSubscription = useCallback(async (agentId: string, channelId: string) => {
    try {
      const token = localStorage.getItem('alluci_daemon_token');
      const response = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/subscriptions/${channelId}`, {
        method: 'DELETE',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'X-CSRF-Token': await getCsrfToken(DAEMON_URL, token) || ''
        }
      });
      return await response.json();
    } catch (err) {
      console.error("Failed to delete subscription:", err);
      return { status: "ERROR" };
    }
  }, []);
  const getStatus = useCallback(async () => {
    try {
      const response = await fetch(`${DAEMON_URL}/health`);
      return await response.json();
    } catch (err) {
      return { status: "DOWN" };
    }
  }, []);

  return { executeObjective, getStatus, getAgentSubscriptions, updateAgentSubscription, deleteAgentSubscription, isBusy };
};
