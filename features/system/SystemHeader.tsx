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
    } = useStore();

    // Apply theme to DOM on mount
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
    }, [theme]);

    const VIEW_TITLES: Record<string, string> = {
        chat: 'Chat',
        soul: 'Soul Preferences',
        skills: 'Skill Manifest',
        bridges: 'Bridge Directory',
        api: 'API Configuration',
        tasks: 'Task Manifold',
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
                    <span className="topbar__subtitle">Sovereign OS v4.3</span>
                </div>
            </div>

            <div className="topbar__center">
                <span className="topbar__view-title">{VIEW_TITLES[activeView] || ''}</span>
            </div>

            <div className="topbar__right">
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
