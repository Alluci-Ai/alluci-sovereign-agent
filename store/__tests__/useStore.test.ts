import { describe, it, expect, beforeEach } from 'vitest';
import { useStore, type ActiveView } from '../useStore';

describe('useStore', () => {
 beforeEach(() => {
   // Reset to initial state before each test
   useStore.setState(useStore.getState());
 });

 // ── Navigation State ────────────────────────────────────────────────────
 it('has default activeView of chat', () => {
   expect(useStore.getState().activeView).toBe('chat');
 });

 it('setActiveView updates activeView', () => {
   useStore.getState().setActiveView('dag');
   expect(useStore.getState().activeView).toBe('dag');
 });

 it('setActiveView accepts all valid views', () => {
   const views: ActiveView[] = ['chat', 'dag', 'memory', 'agents', 'analytics', 'config', 'audit'];
   for (const view of views) {
     useStore.getState().setActiveView(view);
     expect(useStore.getState().activeView).toBe(view);
   }
 });

 // ── Processing State ─────────────────────────────────────────────────────
 it('isProcessing defaults to false', () => {
   expect(useStore.getState().isProcessing).toBe(false);
 });

 it('setIsProcessing toggles correctly', () => {
   useStore.getState().setIsProcessing(true);
   expect(useStore.getState().isProcessing).toBe(true);
   useStore.getState().setIsProcessing(false);
   expect(useStore.getState().isProcessing).toBe(false);
 });

 // ── Biometrics State ─────────────────────────────────────────────────────
 it('updateBiometrics merges new biometric data', () => {
   useStore.getState().updateBiometrics({ hr: 72, hrv: 55 });
   const { biometrics } = useStore.getState();
   expect(biometrics.hr).toBe(72);
   expect(biometrics.hrv).toBe(55);
 });

 // ── Connections State ────────────────────────────────────────────────────
 it('setConnections replaces the connections array', () => {
   const mockConns = [{ id: 'slack', name: 'Slack', status: 'CONNECTED' }] as any;
   useStore.getState().setConnections(mockConns);
   expect(useStore.getState().connections).toHaveLength(1);
   expect(useStore.getState().connections[0].id).toBe('slack');
 });
});
