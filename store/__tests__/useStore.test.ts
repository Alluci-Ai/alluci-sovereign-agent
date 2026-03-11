import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../useStore';

describe('useStore', () => {
  beforeEach(() => {
    useStore.setState(useStore.getInitialState?.() ?? {});
  });

  it('has default activeView of chat', () => {
    expect(useStore.getState().activeView).toBe('chat');
  });

  it('setActiveView updates activeView', () => {
    useStore.getState().setActiveView('dag');
    expect(useStore.getState().activeView).toBe('dag');
  });

  it('isProcessing defaults to false', () => {
    expect(useStore.getState().isProcessing).toBe(false);
  });

  it('setIsProcessing updates correctly', () => {
    useStore.getState().setIsProcessing(true);
    expect(useStore.getState().isProcessing).toBe(true);
  });
});
