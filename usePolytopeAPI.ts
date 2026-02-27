
import { useState, useCallback } from 'react';

const DAEMON_URL = 'http://localhost:8000';

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

      const response = await fetch(`${DAEMON_URL}/objective/execute`, {
        method: 'POST',
        headers: headers,
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

  const getStatus = useCallback(async () => {
    try {
      const response = await fetch(`${DAEMON_URL}/system/status`);
      return await response.json();
    } catch (err) {
      return null;
    }
  }, []);

  return { executeObjective, getStatus, isBusy };
};
