import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CronPanel from '../../features/scheduling/CronPanel';
import React from 'react';

// Mock the store
vi.mock('../../store/useStore', () => ({
  useStore: () => ({
    accessToken: 'test-token',
  }),
}));

// Mock child components
vi.mock('./CronJobForm', () => ({ CronJobForm: () => <div data-testid="cron-form">Cron Form</div> }));
vi.mock('./CronRunHistory', () => ({ CronRunHistory: () => <div data-testid="cron-history">Cron History</div> }));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock window.confirm
global.confirm = vi.fn(() => true);

describe('CronPanel Component', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    vi.clearAllMocks();
  });

  const mockJobs = [
    {
      id: 1,
      name: 'Morning Sync',
      schedule_type: 'cron',
      schedule_value: '0 8 * * *',
      payload: 'Sync data',
      enabled: true,
      last_run_at: '2026-03-22T08:00:00Z',
    },
    {
        id: 2,
        name: 'Weekly Backup',
        schedule_type: 'interval',
        schedule_value: '10080',
        payload: 'Backup',
        enabled: false,
    }
  ];

  it('renders loading state initially', async () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<CronPanel />);
    expect(screen.getByText(/SYNCING_CRON_MANIFOLD/i)).toBeInTheDocument();
  });

  it('renders job list after successful fetch', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockJobs,
    });

    render(<CronPanel />);

    await waitFor(() => {
      expect(screen.getByText('Morning Sync')).toBeInTheDocument();
      expect(screen.getByText('Weekly Backup')).toBeInTheDocument();
    });
  });

  it('toggles job execution state', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockJobs }) // Initial load
             .mockResolvedValueOnce({ ok: true }); // Toggle PUT request

    render(<CronPanel />);

    await waitFor(() => screen.getByText('Morning Sync'));
    
    // Find the pause button (Morning Sync is enabled)
    const pauseBtn = screen.getAllByRole('button')[1]; // Adjust index based on rendered output or test-id
    fireEvent.click(pauseBtn);

    expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/cron/jobs/1'),
        expect.objectContaining({ method: 'PUT' })
    );
  });

  it('filters jobs by status', async () => {
    mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockJobs,
    });

    render(<CronPanel />);

    await waitFor(() => screen.getByText('Morning Sync'));

    const activeFilter = screen.getByText('active');
    fireEvent.click(activeFilter);

    expect(screen.getByText('Morning Sync')).toBeInTheDocument();
    expect(screen.queryByText('Weekly Backup')).not.toBeInTheDocument();
  });

  it('opens history view', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => mockJobs });
    render(<CronPanel />);

    await waitFor(() => screen.getByText('History'));
    fireEvent.click(screen.getByText('History'));

    expect(screen.getByTestId('cron-history')).toBeInTheDocument();
  });
});
