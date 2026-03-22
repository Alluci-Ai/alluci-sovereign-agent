import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WalletPanel } from '../../features/wallet/WalletPanel';
import React from 'react';

// Mock the store
vi.mock('../../store/useStore', () => ({
  useStore: () => ({
    accessToken: 'test-token',
    walletMode: 'lite',
    setWalletMode: vi.fn(),
    walletStatus: 'synced',
    setWalletStatus: vi.fn(),
  }),
}));

// Mock child components
vi.mock('./WalletOverview', () => ({ WalletOverview: () => <div>Wallet Overview</div> }));
vi.mock('./WalletSendReceive', () => ({ WalletSendReceive: () => <div>Send Receive</div> }));
vi.mock('./WalletTransactions', () => ({ WalletTransactions: () => <div>Transactions</div> }));
vi.mock('./WalletMining', () => ({ WalletMining: () => <div>Mining</div> }));
vi.mock('./NodePanel', () => ({ NodePanel: () => <div>Node Panel</div> }));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('WalletPanel Component', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('renders loading state initially', async () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<WalletPanel />);
    expect(screen.getByText(/Syncing wallet with Verus network/i)).toBeInTheDocument();
  });

  it('renders dashboard after successful fetch', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        connected: true,
        total_vrsc: 100,
        unconfirmed: 0,
        balances: [],
        pbaas_chains: [],
        recent_transactions: [],
      }),
    });

    render(<WalletPanel />);

    await waitFor(() => {
      expect(screen.getByText('Sovereign Wallet')).toBeInTheDocument();
    });
    expect(screen.getByText('Wallet Overview')).toBeInTheDocument();
  });

  it('switches tabs between Dashboard and Node Manager', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ connected: true }),
    });

    render(<WalletPanel />);

    await waitFor(() => screen.getByText('Node Manager'));
    
    const nodeTab = screen.getByText('Node Manager');
    fireEvent.click(nodeTab);
    
    expect(screen.getByText('Node Panel')).toBeInTheDocument();
  });
});
