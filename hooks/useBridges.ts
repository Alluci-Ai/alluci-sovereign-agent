import React, { useCallback } from 'react';
import { useStore } from '../store/useStore';

export const useBridges = (
    bridgeManagerRef: React.MutableRefObject<any>,
    securityManagerRef: React.MutableRefObject<any>,
    auditLedgerRef: React.MutableRefObject<any>,
    refreshAuditLog: () => void
) => {
    const {
        setApiKeys,
        setConnections,
        socialEvents, setSocialEvents,
        enterpriseEvents, setEnterpriseEvents
    } = useStore();

    const handleRotateKeys = async () => {
        await bridgeManagerRef.current.performRotateKeys();
        auditLedgerRef.current.addEntry("KEYS_ROTATED", { scope: "ALL_VAULTS" });
        refreshAuditLog();
    };

    const handleFlushCache = async () => {
        await bridgeManagerRef.current.performFlushCache();
        auditLedgerRef.current.addEntry("CACHE_FLUSHED", { scope: "ALL_VAULTS" });
        refreshAuditLog();
    };

    const handleSaveApiKeys = async (newKeys: any, DAEMON_URL: string, geminiServiceRef: any) => {
        setApiKeys(newKeys);
        try {
            const res = await fetch(`${DAEMON_URL}/api/vault/keys`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newKeys),
                credentials: 'include'
            });
            if (res.ok) {
                geminiServiceRef.current?.audit.addEntry("API_MANIFOLD_PERSISTED", { status: "SUCCESS" });
                refreshAuditLog();
            }
        } catch (e) {
            console.error("Vault persistence failed.");
        }
    };

    const handleSocialAction = useCallback((id: string, action: string, params: any) => {
        if (bridgeManagerRef.current) {
            bridgeManagerRef.current.executeSocialTask(id, action, params);
            setSocialEvents([
                { platform: id.toUpperCase(), type: action, msg: 'Manifold task dispatched', time: new Date().toISOString() },
                ...socialEvents
            ].slice(0, 5));
        }
    }, [socialEvents, setSocialEvents, bridgeManagerRef]);

    const handleEnterpriseAction = useCallback((id: string, action: string, params: any) => {
        if (bridgeManagerRef.current) {
            bridgeManagerRef.current.executeEnterpriseTask(id, action, params);
            setEnterpriseEvents([
                { platform: id.toUpperCase(), type: action, msg: 'Enterprise request vaulted', time: new Date().toISOString() },
                ...enterpriseEvents
            ].slice(0, 5));
        }
    }, [enterpriseEvents, setEnterpriseEvents, bridgeManagerRef]);

    const handlePulse = useCallback((id: string) => {
        if (bridgeManagerRef.current) {
            bridgeManagerRef.current.sendMessage(id, 'Self', 'Sovereign Pulse Test');
            auditLedgerRef.current.addEntry("IMESSAGE_PULSE_SENT", { to: 'Self' });
            refreshAuditLog();
        }
    }, [refreshAuditLog, bridgeManagerRef, auditLedgerRef]);

    return {
        handleRotateKeys,
        handleFlushCache,
        handleSaveApiKeys,
        handleSocialAction,
        handleEnterpriseAction,
        handlePulse
    };
};
