import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VerusIdLogin } from './VerusIdLogin';

describe('VerusIdLogin', () => {
    const mockOnComplete = vi.fn();
    const mockOnCancel = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.useRealTimers();
    });

    it('renders loading state initially and fetches login request', async () => {
        // Mock initial fetch
        const mockResponse = {
            request: { challenge: { challenge_id: 'test_challenge' }, signing_id: 'test_id' },
            deeplink: 'verus://test'
        };
        
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        });

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        expect(screen.getByText('[ NEGOTIATING_VDXF_PRIMES ]')).toBeInTheDocument();
        
        await waitFor(() => {
            expect(screen.getByText('Scan with Verus Mobile')).toBeInTheDocument();
        });
        
        expect(screen.getByText('test_id')).toBeInTheDocument();
    });

    it('shows error state when fetch fails', async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: false
        });

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        await waitFor(() => {
            expect(screen.getByText('Configuration Error')).toBeInTheDocument();
        });
        
        expect(screen.getByText('Retry Connection')).toBeInTheDocument();
    });

    it.skip('polls for status and completes on success', async () => {
        vi.useFakeTimers();
        const mockResponse = {
            request: { challenge: { challenge_id: 'test_challenge' } },
            deeplink: 'verus://test'
        };
        
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        });

        // First poll: pending
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => ({ status: 'PENDING' })
        });

        // Second poll: success
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => ({ status: 'SUCCESS', identity: 'alluci@' })
        });

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        // Resolve initial fetch
        await vi.runOnlyPendingTimersAsync();

        // Trigger polls
        for (let i = 0; i < 3; i++) {
            await act(async () => {
                await vi.advanceTimersToNextTimerAsync();
            });
            await vi.runOnlyPendingTimersAsync();
        }

        await waitFor(() => {
            expect(screen.getByText('Authenticated')).toBeInTheDocument();
        });

        // Final timeout
        await act(async () => {
            await vi.advanceTimersToNextTimerAsync();
        });

        expect(mockOnComplete).toHaveBeenCalledWith('alluci@');
        vi.useRealTimers();
    }, 10000);

    it('handles deeplink button click', async () => {
        const mockResponse = {
            request: { challenge: { challenge_id: 'test_challenge' } },
            deeplink: 'verus://test_deeplink'
        };
        
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        });

        // Mock window.location
        const originalLocation = window.location;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        delete (window as any).location;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).location = { ...originalLocation, href: '' };

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        await waitFor(() => {
            expect(screen.getByText('Open in Verus Mobile')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Open in Verus Mobile'));
        expect(window.location.href).toBe('verus://test_deeplink');

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).location = originalLocation;
    });

    it('calls onCancel handled when close button clicked', async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({}) });
        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        fireEvent.click(screen.getByText('✕'));
        expect(mockOnCancel).toHaveBeenCalled();
    });
});
