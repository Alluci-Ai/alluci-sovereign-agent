import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BridgeCenter from '../../components/BridgeCenter';
import React from 'react';

// Mock child components to isolate BridgeCenter testing
vi.mock('../../features/channels/ChannelHealthDashboard', () => ({
  default: () => <div data-testid="health-dashboard">Health Dashboard</div>,
}));
vi.mock('../../features/channels/ChannelConfigExpansion', () => ({
  default: () => <div data-testid="config-expansion">Config Expansion</div>,
}));
vi.mock('../../features/channels/ChannelActionResult', () => ({
  default: () => <div data-testid="action-result">Action Result</div>,
}));
vi.mock('../../features/channels/iMessagePlatformGuard', () => ({
  default: () => <div data-testid="imessage-guard">iMessage Guard</div>,
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Settings: () => <svg data-testid="icon-settings" />,
  ChevronDown: () => <svg data-testid="icon-chevron-down" />,
  ChevronUp: () => <svg data-testid="icon-chevron-up" />,
}));

const mockConnections = [
  {
    id: 'slack',
    name: 'Slack',
    type: 'ENTERPRISE',
    status: 'CONNECTED',
    authType: 'OAUTH',
    accountAlias: 'Workspace A',
    isEncrypted: true,
  },
  {
    id: 'tg',
    name: 'Telegram',
    type: 'SOCIAL',
    status: 'OFFLINE',
    authType: 'TOKEN',
    accountAlias: 'User 1',
    isEncrypted: false,
  },
];

describe('BridgeCenter Component', () => {
  const mockStartAuth = vi.fn();
  const mockSocialAction = vi.fn();
  const mockEnterpriseAction = vi.fn();
  const mockPulse = vi.fn();

  it('renders the health dashboard and grouped connection sections', () => {
    render(
      <BridgeCenter
        connections={mockConnections as any}
        startAuthFlow={mockStartAuth}
        onSocialAction={mockSocialAction}
        onEnterpriseAction={mockEnterpriseAction}
        onPulse={mockPulse}
      />
    );

    expect(screen.getByTestId('health-dashboard')).toBeInTheDocument();
    expect(screen.getByText(/SOCIAL MANIFOLD/i)).toBeInTheDocument();
    expect(screen.getByText(/ENTERPRISE CORE/i)).toBeInTheDocument();
  });

  it('renders connection details correctly in BridgeCard', () => {
    render(
      <BridgeCenter
        connections={mockConnections as any}
        startAuthFlow={mockStartAuth}
        onSocialAction={mockSocialAction}
        onEnterpriseAction={mockEnterpriseAction}
        onPulse={mockPulse}
      />
    );

    expect(screen.getByText('Slack')).toBeInTheDocument();
    expect(screen.getByText('Workspace A')).toBeInTheDocument();
    expect(screen.getByText('E2EE')).toBeInTheDocument();
    expect(screen.getByText('Disconnect')).toBeInTheDocument();
  });

  it('triggers startAuthFlow when Connect/Disconnect is clicked', () => {
    render(
      <BridgeCenter
        connections={mockConnections as any}
        startAuthFlow={mockStartAuth}
        onSocialAction={mockSocialAction}
        onEnterpriseAction={mockEnterpriseAction}
        onPulse={mockPulse}
      />
    );

    const disconnectBtn = screen.getByText('Disconnect');
    fireEvent.click(disconnectBtn);
    expect(mockStartAuth).toHaveBeenCalledWith(expect.objectContaining({ id: 'slack' }));

    const connectBtn = screen.getByText('Connect');
    fireEvent.click(connectBtn);
    expect(mockStartAuth).toHaveBeenCalledWith(expect.objectContaining({ id: 'tg' }));
  });
});
