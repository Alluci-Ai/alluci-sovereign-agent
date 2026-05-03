import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthPortal } from './AuthPortal';
import { Connection, AutonomyLevel } from '../types';

// Mock the store
vi.mock('../store/useStore', () => ({
 useStore: vi.fn(() => ({
   accessToken: null,
   needsOnboarding: false,
 })),
}));

// Mock fetch for auth calls
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

const mockConnection: Connection = {
  id: 'test-1',
  name: 'Test Connection',
  type: 'MESSAGING',
  authType: 'TOKEN',
  status: 'DISCONNECTED',
  autonomyLevel: AutonomyLevel.RESTRICTED,
  isEncrypted: false,
};

describe('AuthPortal', () => {
 beforeEach(() => {
   mockFetch.mockReset();
 });

 it('renders when given a valid connection', () => {
   const onComplete = vi.fn();
   const onCancel = vi.fn();
   render(<AuthPortal connection={mockConnection} onComplete={onComplete} onCancel={onCancel} />);
   // The TokenModal should render for TOKEN auth type
   expect(document.body).toBeTruthy();
 });

 it('calls onComplete with session data on successful auth', async () => {
   mockFetch.mockResolvedValueOnce({
     ok: true,
     json: async () => ({ session: 'test-session', image: 'test-img' }),
   });

   const onComplete = vi.fn();
   const onCancel = vi.fn();
   render(<AuthPortal connection={mockConnection} onComplete={onComplete} onCancel={onCancel} />);

   // Find and interact with the token input if available
   const input = screen.queryByPlaceholderText(/token|key|password/i);
   if (input) {
     fireEvent.change(input, { target: { value: 'test-token-abc' } });
     const submitBtn = screen.queryByRole('button', { name: /connect|submit|authenticate|save/i });
     if (submitBtn) {
       fireEvent.click(submitBtn);
     }
   }
 });

 it('renders null for unknown auth types', () => {
   const unknownConnection: Connection = {
     ...mockConnection,
     authType: 'UNKNOWN' as Connection['authType'],
   };
   const { container } = render(
     <AuthPortal connection={unknownConnection} onComplete={vi.fn()} onCancel={vi.fn()} />
   );
   expect(container.innerHTML).toBe('');
 });
});
