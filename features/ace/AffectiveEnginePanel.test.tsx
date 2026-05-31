import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';
import AffectiveEnginePanel from './AffectiveEnginePanel';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

// Mock Visualizers
vi.mock('../../components/Visualizers', () => ({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    RealtimeBarVisualizer: ({ label, value }: any) => <div data-testid={`viz-${label}`}>{value}</div>,
    CircularVisualizer: () => <div data-testid="circular-viz" />
}));

describe('AffectiveEnginePanel', () => {
    const mockProps = {
        audioStream: null,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        videoRef: { current: null } as any,
        isCameraActive: false,
        toggleCamera: vi.fn(),
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        bridgeManagerRef: { current: { retrieveFromCloud: vi.fn() } } as any,
        accentColor: '#0077FF'
    };

    const mockStore = {
        biometrics: {
            emotional: 0.5,
            physical: 0.6,
            cognitive: 0.4,
            hr: 72,
            hrv: 55,
            respiratoryRate: 14.5,
            sleepEfficiency: 0.85
        },
        updateBiometrics: vi.fn(),
        agent: {
            cognitive: 0.8,
            valenceCurvature: 0.2,
            manifoldIntegrity: 0.9
        },
        harmonicStatus: 'Harmonic_Resonance',
        isConnected: true,
        cloudFiles: [],
        setCloudFiles: vi.fn(),
        mobileView: 'default'
    };

    beforeEach(() => {
        vi.clearAllMocks();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (useStore as any).mockReturnValue(mockStore);
    });

    it('renders biometrics and system coherence visualizers', () => {
        render(<AffectiveEnginePanel {...mockProps} />);
        
        expect(screen.getByTestId('viz-Valence (Emotion)')).toBeInTheDocument();
        expect(screen.getByTestId('viz-Arousal (Physical)')).toBeInTheDocument();
        expect(screen.getByTestId('viz-Cognitive Load')).toBeInTheDocument();
        
        expect(screen.getByTestId('viz-System_Coherence')).toBeInTheDocument();
        expect(screen.getByTestId('viz-Valence_Curvature')).toBeInTheDocument();
        expect(screen.getByTestId('viz-Manifold_Integrity')).toBeInTheDocument();
    });

    it('displays HealthKit metrics correctly', () => {
        render(<AffectiveEnginePanel {...mockProps} />);
        
        expect(screen.getByText('72 BPM')).toBeInTheDocument();
        expect(screen.getByText('55 MS')).toBeInTheDocument();
        expect(screen.getByText('14.5 BR/M')).toBeInTheDocument();
        expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('handles camera toggle', () => {
        render(<AffectiveEnginePanel {...mockProps} />);
        
        const cameraBtn = screen.getByText('[ OPEN_PROBE ]');
        fireEvent.click(cameraBtn);
        expect(mockProps.toggleCamera).toHaveBeenCalled();
    });

    it('handles iCloud file refresh', async () => {
        const mockFiles = [{ name: 'test.pdf', type: 'pdf', size: '1MB' }];
        mockProps.bridgeManagerRef.current.retrieveFromCloud.mockResolvedValueOnce(mockFiles);

        render(<AffectiveEnginePanel {...mockProps} />);
        
        const refreshBtn = screen.getByText('[ REFRESH ]');
        fireEvent.click(refreshBtn);

        await waitFor(() => {
            expect(mockProps.bridgeManagerRef.current.retrieveFromCloud).toHaveBeenCalledWith('icloud', '*');
            expect(mockStore.setCloudFiles).toHaveBeenCalledWith(mockFiles);
        });
    });

    it('displays harmonic status with correct formatting', () => {
        render(<AffectiveEnginePanel {...mockProps} />);
        expect(screen.getByText('HARMONIC_RESONANCE')).toBeInTheDocument();
    });
});
