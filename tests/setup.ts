/**
* Vitest Global Test Setup
* Runs before every test file.
* - Extends vitest expect with jest-dom matchers
* - Sets up MSW (Mock Service Worker) for API mocking
* - Cleans up after each test
*/
import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// ── MSW Handlers: Mock the Polytope Daemon API ──────────────────────────────

export const handlers = [
 http.get('*/api/v1/system/status', () =>
   HttpResponse.json({ status: 'ONLINE', version: '6.4.0' })
 ),
 http.post('*/api/v1/auth/login', () =>
   HttpResponse.json({ access_token: 'test-jwt-token', token_type: 'bearer' })
 ),
 http.get('*/api/v1/auth/me', () =>
   HttpResponse.json({ username: 'test-user', authenticated: true })
 ),
 http.post('*/api/v1/telemetry/ingest', () =>
   HttpResponse.json({ status: 'ok', mode: 'STANDARD' })
 ),
 http.get('*/api/v1/dag/runs', () =>
   HttpResponse.json([])
 ),
 http.post('*/api/v1/objective/execute', () =>
   HttpResponse.json({ run_id: 1, status: 'pending' })
 ),
 http.get('*/api/v1/memory/retrieve', () =>
   HttpResponse.json({ memories: [] })
 ),
 http.get('*/api/v1/goals', () =>
   HttpResponse.json([])
 ),
];

export const server = setupServer(...handlers);

// ── Lifecycle ────────────────────────────────────────────────────────────────

beforeAll(() => {
 server.listen({ onUnhandledRequest: 'warn' });
 vi.spyOn(global, 'fetch');
});

afterEach(() => {
 server.resetHandlers();  // Reset handlers after each test (no cross-contamination)
 vi.mocked(fetch).mockReset();
 cleanup();               // Unmount React components
});

afterAll(() => {
 server.close();
});

// ── Stub browser APIs not available in jsdom ─────────────────────────────────

// SubtleCrypto — used by AuditLedger and BioVault
Object.defineProperty(globalThis, 'crypto', {
 value: {
   getRandomValues: (arr: Uint8Array) => {
     for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
     return arr;
   },
   subtle: {
     // eslint-disable-next-line @typescript-eslint/no-unused-vars
     digest: async (_algo: string, data: BufferSource) => new ArrayBuffer(32),
     generateKey: async () => ({ type: 'secret' }),
     encrypt: async (_algo: unknown, _key: unknown, data: BufferSource) => data,
   },
   randomUUID: () => 'test-uuid-' + Math.random().toString(36).slice(2),
 },
 writable: true,
});

// PublicKeyCredential (WebAuthn) — not available in jsdom
Object.defineProperty(globalThis, 'PublicKeyCredential', {
 value: undefined,
 writable: true,
});

// matchMedia — not available in jsdom
Object.defineProperty(window, 'matchMedia', {
 writable: true,
 value: (query: string) => ({
   matches: false,
   media: query,
   onchange: null,
   addListener: () => {},
   removeListener: () => {},
   addEventListener: () => {},
   removeEventListener: () => {},
   dispatchEvent: () => true,
 }),
});
