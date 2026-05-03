import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { OnboardingWizard } from './OnboardingWizard';
import { useStore } from '../../store/useStore';

// Mock the store
vi.mock('../../store/useStore', () => ({
    useStore: vi.fn()
}));

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
        h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
        p: ({ children, ...props }: any) => <p {...props}>{children}</p>
    },
    AnimatePresence: ({ children }: any) => <>{children}</>
}));

describe('OnboardingFlow', () => {
    it('renders the welcome step initially', () => {
        (useStore as any).mockReturnValue({
            onboardingStep: 0,
            setOnboardingStep: vi.fn(),
            setNeedsOnboarding: vi.fn()
        });

        render(<OnboardingWizard />);
        expect(screen.getByText(/Welcome to the Manifold/i)).toBeInTheDocument();
    });

    it('navigates to next step when Continue/Next is clicked', () => {
        // Step 0 button is "Let's Begin"
        const nextStep = vi.fn();
        // The component uses internal state for 'step', but 'onboardingStep' from store might be what's intended to be mocked if it was used.
        // Looking at the code, it uses local 'step' state initialized to 0.
        // Wait, the component uses LOCAL state for step: const [step, setStep] = useState(0);
        // So I just need to click the button.
        
        const setNeedsOnboarding = vi.fn();
        (useStore as any).mockReturnValue({
            setNeedsOnboarding,
            accessToken: 'mock-token'
        });

        render(<OnboardingWizard />);
        const beginButton = screen.getByText(/Let's Begin/i);
        fireEvent.click(beginButton);
        
        expect(screen.getByRole('heading', { name: /Sovereignty Level/i })).toBeInTheDocument();
    });

    it('calls setNeedsOnboarding(false) when the final step is finished', async () => {
        const setNeedsOnboarding = vi.fn();
        (useStore as any).mockReturnValue({
            setNeedsOnboarding,
            accessToken: 'mock-token'
        });

        // Mock fetch for the onboarding/complete call
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => ({})
        });

        render(<OnboardingWizard />);
        
        // Skip through steps (0 -> 1 -> 2 -> 3 -> 4)
        fireEvent.click(screen.getByText(/Let's Begin/i));
        
        // Step 1: Sovereignty Level (Select Level 3)
        fireEvent.click(screen.getByText(/Full Sovereign/i));
        fireEvent.click(screen.getByText(/Next Step/i));

        // Step 2: Identity
        fireEvent.change(screen.getByPlaceholderText(/e.g. Athena/i), { target: { value: 'TestAgent' } });
        fireEvent.click(screen.getByText(/Next Step/i));
        
        // Step 3: Keys
        fireEvent.change(screen.getByPlaceholderText(/security phrase/i), { target: { value: 'secure-key' } });
        fireEvent.change(screen.getByPlaceholderText(/AIzaSy/i), { target: { value: 'gemini-key' } });
        fireEvent.click(screen.getByText(/Next Step/i));

        // Step 4: Skills & Finish
        const finishButton = screen.getByText(/Initialize Core/i);
        fireEvent.click(finishButton);
        
        // Wait for async finish
        await vi.waitFor(() => {
            expect(setNeedsOnboarding).toHaveBeenCalledWith(false);
        });
    });
});
