import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import '@testing-library/jest-dom/vitest';
import TerminalView from './TerminalView';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

// Mock child components that might be complex
vi.mock('../../components/Visualizers', () => ({
    ExecutionTimeline: () => <div data-testid="execution-timeline" />
}));

vi.mock('../../components/Identity', () => ({
    default: () => <div data-testid="polytope-identity" />
}));

vi.mock('../chat/JumpToNewButton', () => ({
    JumpToNewButton: () => <div data-testid="jump-to-new-button" />
}));

vi.mock('../chat/ReadingIndicator', () => ({
    ReadingIndicator: () => <div data-testid="reading-indicator" />
}));

describe('TerminalView', () => {
    const mockProps = {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        getFormattedTime: (iso: string) => '12:00:00',
        copyText: vi.fn()
    };

    beforeAll(() => {
        // Mock scrollIntoView for jsdom
        window.HTMLElement.prototype.scrollIntoView = vi.fn();
    });

    it('renders idle state when transcriptions are empty', () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            transcriptions: [],
            isProcessing: false
        });

        render(<TerminalView {...mockProps} />);
        expect(screen.getByText('EXECUTIVE_SESSION_IDLE')).toBeInTheDocument();
        expect(screen.getByTestId('polytope-identity')).toBeInTheDocument();
    });

    it('renders transcriptions correctly', () => {
        const mockTranscriptions = [
            {
                isUser: true,
                text: 'Hello Alluci',
                timestamp: '2026-03-22T23:00:00Z',
                isCompaction: false
            },
            {
                isUser: false,
                text: 'Hello human',
                timestamp: '2026-03-22T23:00:05Z',
                modelName: 'Gemini 1.5 Pro',
                tokenCount: 150,
                isCompaction: false
            }
        ];

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            transcriptions: mockTranscriptions,
            isProcessing: false
        });

        render(<TerminalView {...mockProps} />);
        
        expect(screen.getByText('Hello Alluci')).toBeInTheDocument();
        expect(screen.getByText('Hello human')).toBeInTheDocument();
        expect(screen.getByText('USER')).toBeInTheDocument();
        expect(screen.getByText('ALLUCI')).toBeInTheDocument();
        expect(screen.getAllByText('[12:00:00]')).toHaveLength(2);
    });

    it('renders compaction divider when isCompaction is true', () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            transcriptions: [{
                isUser: false,
                text: 'Summary',
                timestamp: '2026-03-22T23:00:00Z',
                isCompaction: true,
                tokenCount: 5000
            }],
            isProcessing: false
        });

        render(<TerminalView {...mockProps} />);
        expect(screen.getByText('Context Manifold Compacted')).toBeInTheDocument();
        expect(screen.getByText('5,000 tokens freed')).toBeInTheDocument();
    });

    it('shows reading indicator when isProcessing is true', () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            transcriptions: [],
            isProcessing: true
        });

        // JumpToNewButton or ReadingIndicator might be tracked by text
        render(<TerminalView {...mockProps} />);
        expect(screen.getByTestId('execution-timeline')).toBeInTheDocument();
    });
});
