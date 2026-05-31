import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BridgeCenter from './BridgeCenter';
import { Connection } from '../types';

const mockConnections: Connection[] = [
    {
        id: 'icloud',
        name: 'iCloud',
        type: 'WORKSPACE',
        status: 'CONNECTED',
        authType: 'OAUTH2',
        accountAlias: 'test@icloud.com',
        isEncrypted: true,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        autonomyLevel: 'SOVEREIGN' as any
    },
    {
        id: 'tg',
        name: 'Telegram',
        type: 'MESSAGING',
        status: 'DISCONNECTED',
        authType: 'TOKEN',
        isEncrypted: true,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        autonomyLevel: 'SEMI_AUTONOMOUS' as any
    }
];

describe('BridgeCenter', () => {
    it('renders connection groups correctly', () => {
        render(
            <BridgeCenter 
                connections={mockConnections} 
                startAuthFlow={vi.fn()}
                onSocialAction={vi.fn()}
                onEnterpriseAction={vi.fn()}
                onPulse={vi.fn()}
            />
        );

        expect(screen.getByText(/Apple Ecosystem/i)).toBeDefined();
        expect(screen.getByText(/Social Manifold/i)).toBeDefined();
        expect(screen.getAllByText(/iCloud/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Telegram/i).length).toBeGreaterThan(0);
    });

    it('shows connected status for bridged accounts', () => {
        render(
            <BridgeCenter 
                connections={mockConnections} 
                startAuthFlow={vi.fn()}
                onSocialAction={vi.fn()}
                onEnterpriseAction={vi.fn()}
                onPulse={vi.fn()}
            />
        );

        expect(screen.getByText('test@icloud.com')).toBeDefined();
        expect(screen.getByText('Disconnect')).toBeDefined();
        expect(screen.getByText('Connect')).toBeDefined();
    });

    it('triggers auth flow when button clicked', () => {
        const startAuthFlow = vi.fn();
        render(
            <BridgeCenter 
                connections={mockConnections} 
                startAuthFlow={startAuthFlow}
                onSocialAction={vi.fn()}
                onEnterpriseAction={vi.fn()}
                onPulse={vi.fn()}
            />
        );

        const connectBtn = screen.getByText('Connect');
        fireEvent.click(connectBtn);
        expect(startAuthFlow).toHaveBeenCalledWith(mockConnections[1]);
    });
});
