// tests/setup.ts
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock EventSource globally (SSE — not available in jsdom)
global.EventSource = vi.fn().mockImplementation(() => ({
  onopen:    null,
  onmessage: null,
  onerror:   null,
  addEventListener: vi.fn(),
  close: vi.fn(),
})) as any;

// Mock fetch for all tests (override per test as needed)
global.fetch = vi.fn();

// Silence console.error for expected React warnings in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (typeof args[0] === 'string' && args[0].includes('Warning:')) return;
    originalError(...args);
  };
});
afterAll(() => { console.error = originalError; });

// Reset all mocks between tests
afterEach(() => {
  vi.clearAllMocks();
});
