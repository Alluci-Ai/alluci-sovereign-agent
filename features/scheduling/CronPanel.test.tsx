import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CronPanel } from './CronPanel';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

// Mock sub-components
vi.mock('./CronJobForm', () => ({ CronJobForm: () => <div data-testid="cron-job-form" /> }));
vi.mock('./CronRunHistory', () => ({ CronRunHistory: () => <div data-testid="cron-run-history" /> }));

describe('CronPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        (useStore as any).mockReturnValue({ accessToken: 'mock-token' });
    });

    it('renders loading state initially', async () => {
        (global.fetch as any).mockImplementation(() => new Promise(() => {}));
        render(<CronPanel />);
        expect(screen.getByText('SYNCING_CRON_MANIFOLD...')).toBeInTheDocument();
    });

    it('fetches and displays cron jobs', async () => {
        const mockJobs = [
            { id: 1, name: 'Daily Backup', schedule_type: 'cron', schedule_value: '0 0 * * *', enabled: true },
            { id: 2, name: 'Hourly Sync', schedule_type: 'interval', schedule_value: '60', enabled: false }
        ];

        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockJobs
        });

        render(<CronPanel />);

        await waitFor(() => {
            expect(screen.getByText('Daily Backup')).toBeInTheDocument();
            expect(screen.getByText('Hourly Sync')).toBeInTheDocument();
        });
    });

    it('handles quick add', async () => {
        (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => [] }); // Initial fetch
        (global.fetch as any).mockResolvedValueOnce({ ok: true }); // POST request

        render(<CronPanel />);

        const nameInput = screen.getByPlaceholderText('Scheduler Label...');
        const valueInput = screen.getByPlaceholderText('Minutes (e.g. 60)');
        const addButton = screen.getByText('Add Scheduler');

        fireEvent.change(nameInput, { target: { value: 'New Task' } });
        fireEvent.change(valueInput, { target: { value: '30' } });
        fireEvent.click(addButton);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/cron/jobs'),
                expect.objectContaining({
                    method: 'POST',
                    body: expect.stringContaining('"name":"New Task"')
                })
            );
        });
    });

    it('toggles job enabled state', async () => {
        const mockJob = { id: 1, name: 'Job', enabled: true, schedule_type: 'cron' };
        (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => [mockJob] });
        (global.fetch as any).mockResolvedValueOnce({ ok: true }); // PUT request

        render(<CronPanel />);
        
        await waitFor(() => {
            expect(screen.getByText('Job')).toBeInTheDocument();
        });

        const toggleBtn = screen.getByRole('button', { name: '' }); // The pause/play icon button
        fireEvent.click(toggleBtn);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/cron/jobs/1'),
                expect.objectContaining({
                    method: 'PUT',
                    body: expect.stringContaining('"enabled":false')
                })
            );
        });
    });

    it('deletes a job after confirmation', async () => {
        const mockJob = { id: 1, name: 'Job', enabled: true, schedule_type: 'cron' };
        (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => [mockJob] });
        (global.fetch as any).mockResolvedValueOnce({ ok: true }); // DELETE request
        
        window.confirm = vi.fn().mockReturnValue(true);

        render(<CronPanel />);
        
        await waitFor(() => {
            expect(screen.getByText('Job')).toBeInTheDocument();
        });

        const deleteBtn = screen.getByTitle('Discard');
        fireEvent.click(deleteBtn);

        expect(window.confirm).toHaveBeenCalled();
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/cron/jobs/1'),
                expect.objectContaining({ method: 'DELETE' })
            );
        });
    });

    it('switches to History view', async () => {
        (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => [] });
        
        render(<CronPanel />);
        
        fireEvent.click(screen.getByText('History'));
        expect(screen.getByTestId('cron-run-history')).toBeInTheDocument();
        
        fireEvent.click(screen.getByText('Back to Jobs'));
        expect(screen.queryByTestId('cron-run-history')).not.toBeInTheDocument();
    });
});
