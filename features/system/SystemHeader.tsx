import React, { useEffect } from 'react';
import { useStore } from '../../store/useStore';
import PolytopeIdentity from '../../components/Identity';
import { HeartbeatIndicator } from '../../components/Visualizers';
import { Menu, Sun, Moon } from 'lucide-react';

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
        operatingMode,
        setOperatingMode
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
                    <span className="topbar__subtitle">Sovereign OS Beta v1.1.1</span>
                </div>
            </div>

            <div className="topbar__center flex items-center gap-4">
                <span className="topbar__view-title hidden lg:block">{VIEW_TITLES[activeView] || ''}</span>
            </div>

            <div className="topbar__right">
                <HeartbeatIndicator status={daemonStatus} />

                {/* Theme toggle */}
                <button
                    onClick={toggleTheme}
                    className="topbar__theme-btn rounded-full"
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

                {/* Lite / Sovereign toggle */}
                <div className="topbar__mode-toggle">
                    <button
                        onClick={() => setOperatingMode('LITE')}
                        className={`topbar__mode-btn ${operatingMode === 'LITE' ? 'topbar__mode-btn--active topbar__mode-btn--cloud' : ''}`}
                    >
                        Lite
                    </button>
                    <button
                        onClick={() => setOperatingMode('FULL_SOVEREIGN')}
                        className={`topbar__mode-btn ${operatingMode === 'FULL_SOVEREIGN' ? 'topbar__mode-btn--active topbar__mode-btn--local' : ''}`}
                    >
                        Sovereign
                    </button>
                </div>
            </div>
        </header>
    );
};

export default SystemHeader;
