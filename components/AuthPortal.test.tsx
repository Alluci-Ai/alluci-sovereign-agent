import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { AuthPortal } from './AuthPortal';

// Mock the features/channels/auth components
vi.mock('../features/channels/auth/OAuthModal', () => ({
    OAuthModal: ({ onCancel }: { onCancel: () => void }) => <div data-testid="oauth-modal"><button onClick={onCancel}>Cancel</button></div>
}));
vi.mock('../features/channels/auth/TokenModal', () => ({
    TokenModal: () => <div data-testid="token-modal" />
}));
vi.mock('../features/channels/auth/QRSyncModal', () => ({
    QRSyncModal: () => <div data-testid="qr-sync-modal" />
}));
vi.mock('../features/channels/auth/SecureTunnelModal', () => ({
    SecureTunnelModal: () => <div data-testid="secure-tunnel-modal" />
}));
vi.mock('../features/channels/auth/WebSessionModal', () => ({
    WebSessionModal: () => <div data-testid="web-session-modal" />
}));
vi.mock('../features/channels/auth/VerusIdentityModal', () => ({
    VerusIdentityModal: () => <div data-testid="verus-identity-modal" />
}));

describe('AuthPortal', () => {
    const mockOnComplete = vi.fn();
    const mockOnCancel = vi.fn();

    it('renders OAuthModal for OAUTH2 authType', () => {
        const connection = { authType: 'OAUTH2' } as any;
        render(<AuthPortal connection={connection} onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        expect(screen.getByTestId('oauth-modal')).toBeInTheDocument();
        
        fireEvent.click(screen.getByText('Cancel'));
        expect(mockOnCancel).toHaveBeenCalled();
    });

    it('renders TokenModal for TOKEN authType', () => {
        const connection = { authType: 'TOKEN' } as any;
        render(<AuthPortal connection={connection} onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        expect(screen.getByTestId('token-modal')).toBeInTheDocument();
    });

    it('renders QRSyncModal for QR_SYNC authType', () => {
        const connection = { authType: 'QR_SYNC' } as any;
        render(<AuthPortal connection={connection} onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        expect(screen.getByTestId('qr-sync-modal')).toBeInTheDocument();
    });

    it('renders VerusIdentityModal for IDENTITY_LINK authType', () => {
        const connection = { authType: 'IDENTITY_LINK' } as any;
        render(<AuthPortal connection={connection} onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        expect(screen.getByTestId('verus-identity-modal')).toBeInTheDocument();
    });

    it('returns null for unknown authType', () => {
        const connection = { authType: 'UNKNOWN' } as any;
        const { container } = render(<AuthPortal connection={connection} onComplete={mockOnComplete} onCancel={mockOnCancel} />);
        expect(container.firstChild).toBeNull();
    });
});
