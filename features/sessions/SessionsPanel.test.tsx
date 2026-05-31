import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SessionsPanel } from './SessionsPanel';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

describe('SessionsPanel', () => {
    const mockSetSessions = vi.fn();
    const mockSetActiveSessionKey = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            sessions: [],
            setSessions: mockSetSessions,
            setActiveSessionKey: mockSetActiveSessionKey,
            accessToken: 'test-token'
        });

        // Mock fetch
        global.fetch = vi.fn().mockImplementation(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ sessions: [] })
            })
        );
    });

    it('renders the session manifold header', () => {
        render(<SessionsPanel />);
        expect(screen.getByText('Sessions Manifold')).toBeDefined();
        expect(screen.getByText('Initialize New Protocol')).toBeDefined();
    });

    it('fetches sessions on mount', async () => {
        render(<SessionsPanel />);
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/sessions'), expect.anything());
        });
    });

    it('displays "No active session footprints detected." when sessions list is empty', async () => {
        render(<SessionsPanel />);
        expect(await screen.findByText(/No active session footprints detected/i)).toBeDefined();
    });
});
