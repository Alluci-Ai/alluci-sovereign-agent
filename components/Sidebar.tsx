import React from 'react';
import { useStore, ActiveView } from '../store/useStore';
import AffectiveWidget from './AffectiveWidget';
import {
    MessageSquare, Brain, Zap, Link2, Key,
    CheckSquare, FolderOpen, Shield, ChevronLeft, ChevronRight,
    LayoutList, BarChart3, Calendar, Bot, Settings, ScrollText, Bug
} from 'lucide-react';

interface NavItem {
    id: ActiveView;
    label: string;
    icon: React.FC<any>;
}

const NAV_ITEMS: NavItem[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'sessions', label: 'Sessions', icon: LayoutList },
    { id: 'soul', label: 'Soul', icon: Brain },
    { id: 'skills', label: 'Skills', icon: Zap },
    { id: 'bridges', label: 'Bridges', icon: Link2 },
    { id: 'agents', label: 'Agents', icon: Bot },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'scheduling', label: 'Scheduling', icon: Calendar },
    { id: 'api', label: 'API', icon: Key },
    { id: 'config', label: 'Config', icon: Settings },
    { id: 'tasks', label: 'Tasks', icon: CheckSquare },
    { id: 'logs', label: 'Logs', icon: ScrollText },
    { id: 'debug', label: 'Debug', icon: Bug },
    { id: 'files', label: 'Files', icon: FolderOpen },
    { id: 'audit', label: 'Audit', icon: Shield },
];

interface SidebarProps {
    audioStream: MediaStream | null;
    videoRef: React.RefObject<HTMLVideoElement | null>;
    isCameraActive: boolean;
    toggleCamera: () => void;
    bridgeManagerRef: React.RefObject<any>;
    accentColor: string;
}

const Sidebar: React.FC<SidebarProps> = ({
    audioStream,
    videoRef,
    isCameraActive,
    toggleCamera,
    bridgeManagerRef,
    accentColor,
}) => {
    const {
        activeView, setActiveView,
        isSidebarCollapsed, setSidebarCollapsed,
        isConnected
    } = useStore();

    return (
        <aside
            className={`sidebar ${isSidebarCollapsed ? 'sidebar--collapsed' : ''}`}
        >
            {/* Collapse / Expand toggle */}
            <button
                onClick={() => setSidebarCollapsed(!isSidebarCollapsed)}
                className="sidebar__toggle"
                title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
                {isSidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>

            {/* Navigation items */}
            <nav className="sidebar__nav">
                {NAV_ITEMS.map(item => {
                    const Icon = item.icon;
                    const isActive = activeView === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setActiveView(item.id)}
                            className={`sidebar__item ${isActive ? 'sidebar__item--active' : ''}`}
                            title={isSidebarCollapsed ? item.label : undefined}
                        >
                            <Icon size={18} strokeWidth={isActive ? 2.2 : 1.6} />
                            {!isSidebarCollapsed && (
                                <span className="sidebar__item-label">{item.label}</span>
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Affective Engine widget at bottom */}
            {!isSidebarCollapsed && (
                <AffectiveWidget
                    audioStream={audioStream}
                    videoRef={videoRef}
                    isCameraActive={isCameraActive}
                    toggleCamera={toggleCamera}
                    bridgeManagerRef={bridgeManagerRef}
                    accentColor={accentColor}
                />
            )}
        </aside>
    );
};

export default Sidebar;
