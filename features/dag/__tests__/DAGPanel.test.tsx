// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DAGPanel } from '../DAGPanel';

// Mock the store
vi.mock('../../../store/useStore', () => ({
  useStore: () => ({ accessToken: 'test-token', setActiveRunId: vi.fn() }),
}));

// Mock child hooks
vi.mock('../hooks/useDAGRuns', () => ({
  useDAGRuns: () => ({
    runs: [
      { id: 1, objective: 'Test run', status: 'completed',
        started_at: new Date().toISOString(), task_counts: { total: 3, completed: 3, failed: 0, running: 0, pending: 0 } }
    ],
    loading: false, error: null, refresh: vi.fn(), hasMore: false,
  }),
}));

vi.mock('../hooks/useTaskStream', () => ({
  useTaskStream: () => ({ taskStates: {}, streamStatus: 'idle', disconnect: vi.fn() }),
}));

describe('DAGPanel', () => {
  it('renders the panel with run list', async () => {
    render(<DAGPanel />);
    await waitFor(() => {
      expect(screen.getByText('DAG Planner')).toBeInTheDocument();
    });
  });

  it('shows EXECUTION_MANIFOLD label', async () => {
    render(<DAGPanel />);
    await waitFor(() => {
      expect(screen.getByText('EXECUTION_MANIFOLD')).toBeInTheDocument();
    });
  });

  it('shows empty state when no run is selected', async () => {
    render(<DAGPanel />);
    await waitFor(() => {
      expect(screen.getByText(/SELECT_RUN_TO_VISUALIZE/i)).toBeInTheDocument();
    });
  });

  it('shows the objective submit bar', async () => {
    render(<DAGPanel />);
    await waitFor(() => {
      expect(screen.getByText(/NEW_OBJECTIVE/i)).toBeInTheDocument();
    });
  });
});
