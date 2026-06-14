import { render, screen, fireEvent } from '@testing-library/react';
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

vi.mock('mermaid', () => ({
    default: {
        initialize: vi.fn(),
        render: vi.fn().mockResolvedValue({ svg: '<svg data-testid="mock-mermaid-svg"></svg>' })
    }
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

        // Mock ResizeObserver for JSDOM
        class MockResizeObserver {
            observe = vi.fn();
            unobserve = vi.fn();
            disconnect = vi.fn();
        }
        window.ResizeObserver = MockResizeObserver as any;
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

    it('renders mermaid and other code blocks correctly', async () => {
        const mockTranscriptions = [
            {
                isUser: false,
                text: 'Here is a diagram:\n```mermaid\ngraph TD\nA --> B\n```\nAnd code:\n```javascript\nconsole.log("hello");\n```',
                timestamp: '2026-03-22T23:00:00Z',
                isCompaction: false
            }
        ];

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            transcriptions: mockTranscriptions,
            isProcessing: false
        });

        render(<TerminalView {...mockProps} />);

        // It should render loading indicator or mermaid diagram
        expect(screen.getByText('Rendering diagram...')).toBeInTheDocument();
        expect(screen.getByText('console.log("hello");')).toBeInTheDocument();

        // Wait for async rendering of SVG
        const svg = await screen.findByTestId('mock-mermaid-svg');
        expect(svg).toBeInTheDocument();
    });

    it('supports click-to-expand and close on mermaid diagrams', async () => {
        const mockTranscriptions = [
            {
                isUser: false,
                text: '```mermaid\ngraph TD\nA --> B\n```',
                timestamp: '2026-03-22T23:00:00Z',
                isCompaction: false
            }
        ];

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue({
            transcriptions: mockTranscriptions,
            isProcessing: false
        });

        render(<TerminalView {...mockProps} />);

        // Wait for diagram SVG to render
        const diagram = await screen.findByTestId('mermaid-clickable-diagram');
        expect(diagram).toBeInTheDocument();

        // Modal should not be visible initially
        expect(screen.queryByTestId('mermaid-modal-backdrop')).not.toBeInTheDocument();

        // Click the diagram to expand
        fireEvent.click(diagram);

        // Modal backdrop and close button should now be in the document
        const backdrop = screen.getByTestId('mermaid-modal-backdrop');
        const closeBtn = screen.getByTestId('mermaid-modal-close');
        expect(backdrop).toBeInTheDocument();
        expect(closeBtn).toBeInTheDocument();

        // Check zoom controls
        const zoomIn = screen.getByTestId('mermaid-zoom-in');
        const zoomOut = screen.getByTestId('mermaid-zoom-out');
        const zoomReset = screen.getByTestId('mermaid-zoom-reset');
        expect(zoomIn).toBeInTheDocument();
        expect(zoomOut).toBeInTheDocument();
        expect(zoomReset).toBeInTheDocument();

        // Click controls to verify they handle actions gracefully
        fireEvent.click(zoomIn);
        fireEvent.click(zoomOut);
        fireEvent.click(zoomReset);

        // Click the close button to dismiss the modal
        fireEvent.click(closeBtn);

        // Modal backdrop should be removed
        expect(screen.queryByTestId('mermaid-modal-backdrop')).not.toBeInTheDocument();
    });
});
