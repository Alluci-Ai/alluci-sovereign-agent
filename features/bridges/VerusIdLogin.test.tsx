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
        (global.fetch as any).mockResolvedValueOnce({
            ok: false
        });

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        await waitFor(() => {
            expect(screen.getByText('Configuration Error')).toBeInTheDocument();
        });
        
        expect(screen.getByText('Retry Connection')).toBeInTheDocument();
    });

    it('polls for status and completes on success', async () => {
        vi.useFakeTimers();
        const mockResponse = {
            request: { challenge: { challenge_id: 'test_challenge' } },
            deeplink: 'verus://test'
        };
        
        // Initial request
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        });

        // First poll: pending
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => ({ status: 'PENDING' })
        });

        // Second poll: success
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => ({ status: 'SUCCESS', identity: 'alluci@' })
        });

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        await waitFor(() => {
            expect(screen.getByText('Scan with Verus Mobile')).toBeInTheDocument();
        });

        // Advance timers for polling
        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });

        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });

        await waitFor(() => {
            expect(screen.getByText('Authenticated')).toBeInTheDocument();
        });

        // Advance for the 1500ms timeout to onComplete
        await act(async () => {
            await vi.advanceTimersByTimeAsync(1500);
        });

        expect(mockOnComplete).toHaveBeenCalledWith('alluci@');
        vi.useRealTimers();
    });

    it('handles deeplink button click', async () => {
        const mockResponse = {
            request: { challenge: { challenge_id: 'test_challenge' } },
            deeplink: 'verus://test_deeplink'
        };
        
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        });

        // Mock window.location
        const originalLocation = window.location;
        delete (window as any).location;
        (window as any).location = { ...originalLocation, href: '' };

        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        await waitFor(() => {
            expect(screen.getByText('Open in Verus Mobile')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Open in Verus Mobile'));
        expect(window.location.href).toBe('verus://test_deeplink');

        (window as any).location = originalLocation;
    });

    it('calls onCancel handled when close button clicked', async () => {
        (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({}) });
        render(<VerusIdLogin onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        
        fireEvent.click(screen.getByText('✕'));
        expect(mockOnCancel).toHaveBeenCalled();
    });
});
