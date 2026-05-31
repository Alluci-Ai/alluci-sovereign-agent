import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WalletPanel } from './WalletPanel';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

// Mock sub-components
vi.mock('./WalletOverview', () => ({ WalletOverview: () => <div data-testid="wallet-overview" /> }));
vi.mock('./WalletSendReceive', () => ({ WalletSendReceive: () => <div data-testid="wallet-send-receive" /> }));
vi.mock('./WalletTransactions', () => ({ WalletTransactions: () => <div data-testid="wallet-transactions" /> }));
vi.mock('./WalletMining', () => ({ WalletMining: () => <div data-testid="wallet-mining" /> }));
vi.mock('./NodePanel', () => ({ NodePanel: () => <div data-testid="node-panel" /> }));

describe('WalletPanel', () => {
    const storeState = {
        accessToken: 'mock-token',
        walletMode: 'lite',
        walletStatus: 'offline',
        setWalletMode: vi.fn((m) => { storeState.walletMode = m; }),
        setWalletStatus: vi.fn((s) => { storeState.walletStatus = s; }),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.useRealTimers();
        storeState.walletMode = 'lite';
        storeState.walletStatus = 'offline';
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue(storeState);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('renders loading state initially', async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockImplementation(() => new Promise(() => {})); // Never resolves
        render(<WalletPanel />);
        expect(screen.getByText('Syncing wallet with Verus network...')).toBeInTheDocument();
    });

    it('fetches dashboard data and renders components', async () => {
        const mockDashboard = {
            connected: true,
            total_vrsc: 100,
            unconfirmed: 0,
            balances: [],
            mining: { generating: false, staking: true },
            recent_transactions: [],
            pbaas_chains: ['VRSCTEST']
        };

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValueOnce({
            ok: true,
            json: async () => mockDashboard
        });

        render(<WalletPanel />);

        await waitFor(() => {
            expect(screen.getByTestId('wallet-overview')).toBeInTheDocument();
        });

        expect(storeState.setWalletStatus).toHaveBeenCalledWith('synced');
        expect(screen.getByText('System Online')).toBeInTheDocument();
    });

    it('handles switching to Sovereign mode', async () => {
        const mockDashboard = { connected: true };
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValue({ ok: true, json: async () => mockDashboard });
        
        window.confirm = vi.fn().mockReturnValue(true);

        render(<WalletPanel />);
        
        await waitFor(() => {
            expect(screen.getByText('Go Sovereign')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Go Sovereign'));

        expect(window.confirm).toHaveBeenCalled();
        expect(storeState.setWalletMode).toHaveBeenCalledWith('sovereign');
        
        // Should trigger node start action
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/wallet/node/action'),
            expect.objectContaining({ method: 'POST' })
        );
    });

    it('toggles between Dashboard and Node tabs', async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({ connected: true }) });
        
        render(<WalletPanel />);
        
        await waitFor(() => {
            expect(screen.getByTestId('wallet-overview')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Node Manager'));
        expect(screen.getByTestId('node-panel')).toBeInTheDocument();
        expect(screen.queryByTestId('wallet-overview')).not.toBeInTheDocument();

        fireEvent.click(screen.getByText('Dashboard'));
        expect(screen.getByTestId('wallet-overview')).toBeInTheDocument();
    });

    it('polls for updates every 15 seconds', async () => {
        vi.useFakeTimers();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({ connected: true }) });
        
        render(<WalletPanel />);
        
        await vi.waitFor(() => {
            expect(global.fetch).toHaveBeenCalledTimes(1);
        });

        await act(async () => {
            vi.advanceTimersByTime(15000);
        });

        expect(global.fetch).toHaveBeenCalledTimes(2);
    });
});
