import React, { useEffect } from 'react';
import { useStore } from '../../store/useStore';
import PolytopeIdentity from '../../components/Identity';
import { HeartbeatIndicator } from '../../components/Visualizers';
import { Menu, Sun, Moon } from 'lucide-react';
import { SessionSelector } from '../sessions/SessionSelector';
import { ThinkingLevelToggle } from '../chat/ThinkingLevelToggle';
import { FocusModeToggle } from '../chat/FocusModeToggle';
import SessionKeyPill from '../shell/SessionKeyPill';
import PresenceCountBadge from '../shell/PresenceCountBadge';

interface SystemHeaderProps {
    isConnected: boolean;
    accentColor: string;
    handleConnect: () => void;
    sovereignMode: boolean;
    setSovereignMode: (val: boolean) => void;
}

const SystemHeader: React.FC<SystemHeaderProps> = ({
    isConnected,
    accentColor,
    handleConnect,
    sovereignMode,
    setSovereignMode
}) => {
    const {
        daemonStatus,
        activeView,
        isSidebarCollapsed,
        setSidebarCollapsed,
        setIsMobileMenuOpen,
        theme,
        toggleTheme,
    } = useStore();

    // Apply theme to DOM on mount
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
    }, [theme]);

    const VIEW_TITLES: Record<string, string> = {
        chat: 'Chat',
        sessions: 'Sessions',
        soul: 'Soul Preferences',
        skills: 'Skill Manifest',
        bridges: 'Bridge Directory',
        agents: 'Agents',
        analytics: 'Usage Analytics',
        scheduling: 'Scheduling',
        api: 'API Configuration',
        config: 'Configuration',
        tasks: 'Task Manifold',
        logs: 'Logs',
        debug: 'Debug & Diagnostics',
        files: 'File Manifold',
        audit: 'Audit Ledger',
        canvas: 'A2UI Canvas',
    };

    return (
        <header className="topbar">
            <div className="topbar__left">
                <button
                    onClick={() => {
                        if (window.innerWidth < 768) {
                            setIsMobileMenuOpen(true);
                        } else {
                            setSidebarCollapsed(!isSidebarCollapsed);
                        }
                    }}
                    className="topbar__menu-btn"
                >
                    <Menu size={18} />
                </button>
                <PolytopeIdentity color={accentColor} size={22} active={isConnected} />
                <div className="topbar__brand">
                    <h1 className="topbar__title">POLYTOPE</h1>
                    <span className="topbar__subtitle">Sovereign OS Beta v4.3</span>
                </div>
            </div>

            <div className="topbar__center flex items-center gap-4">
                <span className="topbar__view-title">{VIEW_TITLES[activeView] || ''}</span>
                {activeView === 'chat' && (
                    <div className="hidden md:flex items-center gap-3 ml-4 animate-in fade-in zoom-in duration-300">
                        <SessionSelector />
                        <div className="h-4 w-px bg-glass-edge mx-1" />
                        <ThinkingLevelToggle />
                        <FocusModeToggle />
                    </div>
                )}
            </div>

            <div className="topbar__right">
                <div className="hidden md:flex items-center gap-2 mr-2 animate-in fade-in duration-300">
                    <SessionKeyPill />
                    <PresenceCountBadge />
                </div>

                <HeartbeatIndicator active={daemonStatus === 'ONLINE'} />

                {/* Theme toggle */}
                <button
                    onClick={toggleTheme}
                    className="topbar__theme-btn"
                    title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                >
                    {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                </button>

                {/* Cloud / Local toggle */}
                <div className="topbar__mode-toggle">
                    <button
                        onClick={() => setSovereignMode(false)}
                        className={`topbar__mode-btn ${!sovereignMode ? 'topbar__mode-btn--active topbar__mode-btn--cloud' : ''}`}
                    >
                        Cloud
                    </button>
                    <button
                        onClick={() => setSovereignMode(true)}
                        className={`topbar__mode-btn ${sovereignMode ? 'topbar__mode-btn--active topbar__mode-btn--local' : ''}`}
                    >
                        Local
                    </button>
                </div>

                <button
                    onClick={handleConnect}
                    className={`topbar__connect-btn ${isConnected ? 'topbar__connect-btn--connected' : ''}`}
                >
                    {isConnected ? 'Sleep' : 'Awaken'}
                </button>
            </div>
        </header>
    );
};

export default SystemHeader;
