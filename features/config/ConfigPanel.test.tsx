import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { ConfigPanel } from './ConfigPanel';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

const mockSchema = {
    title: "Daemon Settings",
    type: "object",
    properties: {
        DAEMON_PUBLIC_URL: {
            title: "Public URL",
            type: "string",
            description: "Root endpoint for the daemon"
        },
        JWT_SECRET_KEY: {
            title: "Secret Key",
            type: "string",
            description: "Used for signing tokens"
        }
    }
};

const mockConfig = {
    DAEMON_PUBLIC_URL: "http://localhost:8000",
    JWT_SECRET_KEY: "**********"
};

describe('ConfigPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            accessToken: 'test-token'
        });

        // Mock fetch for both config and schema
        global.fetch = vi.fn().mockImplementation((url) => {
            if (url.includes('/config/schema')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(mockSchema)
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve(mockConfig)
            });
        });
    });

    it('renders the config panel header', () => {
        render(<ConfigPanel />);
        expect(screen.getByText('Daemon Configuration')).toBeDefined();
    });

    it('switches between Form and Raw mode', async () => {
        render(<ConfigPanel />);
        const rawBtn = screen.getByText('Raw JSON');
        fireEvent.click(rawBtn);
        
        // Should show the textarea in raw mode
        await waitFor(() => {
            expect(screen.getByDisplayValue(/DAEMON_PUBLIC_URL/)).toBeDefined();
        });
    });

    it('masks sensitive fields by default', async () => {
        render(<ConfigPanel />);
        await waitFor(() => {
            const secretInput = screen.getByPlaceholderText('Enter JWT_SECRET_KEY...');
            expect((secretInput as HTMLInputElement).type).toBe('password');
        });
    });
});
