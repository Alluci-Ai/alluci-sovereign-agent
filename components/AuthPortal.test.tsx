import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthPortal } from './AuthPortal';

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

describe('AuthPortal', () => {
 beforeEach(() => {
   mockFetch.mockReset();
 });

 it('renders the login form when no access token', () => {
   render(<AuthPortal onAuthenticated={vi.fn()} />);
   expect(screen.getByRole('heading', { name: /alluci|sovereign|login/i })).toBeInTheDocument();
 });

 it('calls onAuthenticated with token on successful login', async () => {
   mockFetch.mockResolvedValueOnce({
     ok: true,
     json: async () => ({ access_token: 'test-token-abc' }),
   });

   const onAuth = vi.fn();
   render(<AuthPortal onAuthenticated={onAuth} />);

   const input = screen.getByPlaceholderText(/master key|password|key/i);
   fireEvent.change(input, { target: { value: 'test-master-key' } });
   fireEvent.click(screen.getByRole('button', { name: /login|connect|authenticate/i }));

   await waitFor(() => {
     expect(onAuth).toHaveBeenCalledWith('test-token-abc');
   });
 });

 it('shows an error message on failed login', async () => {
   mockFetch.mockResolvedValueOnce({
     ok: false,
     json: async () => ({ detail: 'Invalid credentials' }),
   });

   render(<AuthPortal onAuthenticated={vi.fn()} />);

   const input = screen.getByPlaceholderText(/master key|password|key/i);
   fireEvent.change(input, { target: { value: 'wrong-key' } });
   fireEvent.click(screen.getByRole('button', { name: /login|connect|authenticate/i }));

   await waitFor(() => {
     expect(screen.getByText(/invalid|error|failed/i)).toBeInTheDocument();
   });
 });
});
