import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryPanel } from './MemoryPanel';
import { useStore } from '../../store/useStore';
import { sovereignService } from '../../sovereignService';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

// Mock the sovereignService
vi.mock('../../sovereignService', () => ({
    sovereignService: {
        listMemories: vi.fn(),
        deleteMemory: vi.fn(),
        _fetch: vi.fn()
    }
}));

// Mock sub-components
vi.mock('../../components/Memory/HLSMStats', () => ({ HLSMStats: () => <div data-testid="hlsm-stats" /> }));
vi.mock('../../components/Memory/ConsolidationTrigger', () => ({ ConsolidationTrigger: () => <div data-testid="consolidation-trigger" /> }));

describe('MemoryPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (useStore as any).mockReturnValue({ accessToken: 'mock-token' });
    });

    it('renders empty state when no memories exist', async () => {
        (sovereignService.listMemories as any).mockResolvedValueOnce({ entries: [] });
        render(<MemoryPanel onClose={() => {}} />);
        
        await waitFor(() => {
            expect(screen.getByText('Manifold Void — No active memories')).toBeInTheDocument();
        });
    });

    it('fetches and displays memories with correct tiers', async () => {
        const mockMemories = [
            { id: 'mem-1', content: 'Working memory', tier: 0, retention_score: 0.9, source: 'UI' },
            { id: 'mem-2', content: 'Episodic memory', tier: 1, retention_score: 0.7, source: 'CHAT' },
            { id: 'mem-3', content: 'Semantic memory', tier: 2, retention_score: 1.0, source: 'RESEARCH' }
        ];

        (sovereignService.listMemories as any).mockResolvedValueOnce({ entries: mockMemories });
        
        render(<MemoryPanel onClose={() => {}} />);

        await waitFor(() => {
            expect(screen.getByText('Working memory')).toBeInTheDocument();
            expect(screen.getByText('Episodic memory')).toBeInTheDocument();
            expect(screen.getByText('Semantic memory')).toBeInTheDocument();
        });

        expect(screen.getByText('Tier 0 Working')).toBeInTheDocument();
        expect(screen.getByText('Tier 1 Episodic')).toBeInTheDocument();
        expect(screen.getByText('Tier 2 Semantic')).toBeInTheDocument();
    });

    it('handles searching memories', async () => {
        (sovereignService.listMemories as any).mockResolvedValueOnce({ entries: [] });
        const mockSearchResults = [
            { id: 'search-1', content: 'Found memory', tier: 1 }
        ];
        (sovereignService as any)._fetch.mockResolvedValueOnce(mockSearchResults);

        render(<MemoryPanel onClose={() => {}} />);

        const searchInput = screen.getByPlaceholderText('Search manifold content...');
        fireEvent.change(searchInput, { target: { value: 'test query' } });
        fireEvent.keyDown(searchInput, { key: 'Enter' });

        await waitFor(() => {
            expect(screen.getByText('Found memory')).toBeInTheDocument();
        });

        expect((sovereignService as any)._fetch).toHaveBeenCalledWith(expect.stringContaining('/memory/search?q=test%20query'));
    });

    it('handles deleting a memory', async () => {
        const mockMemory = { id: 'delete-me', content: 'Delete this', tier: 1, retention_score: 0.5 };
        (sovereignService.listMemories as any).mockResolvedValueOnce({ entries: [mockMemory] });
        (sovereignService.deleteMemory as any).mockResolvedValueOnce({ status: 'SUCCESS' });

        render(<MemoryPanel onClose={() => {}} />);

        await waitFor(() => {
            expect(screen.getByText('Delete this')).toBeInTheDocument();
        });

        const deleteBtn = screen.getByRole('button', { name: '' }); // Trash icon
        fireEvent.click(deleteBtn);

        await waitFor(() => {
            expect(sovereignService.deleteMemory).toHaveBeenCalledWith('delete-me');
            expect(screen.queryByText('Delete this')).not.toBeInTheDocument();
        });
    });

    it('renders HLSM components', async () => {
        (sovereignService.listMemories as any).mockResolvedValueOnce({ entries: [] });
        render(<MemoryPanel onClose={() => {}} />);
        expect(screen.getByTestId('hlsm-stats')).toBeInTheDocument();
        expect(screen.getByTestId('consolidation-trigger')).toBeInTheDocument();
    });
});
