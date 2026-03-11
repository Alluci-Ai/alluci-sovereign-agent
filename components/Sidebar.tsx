import React, { useState } from 'react';
import { useStore, ActiveView } from '../store/useStore';
import AffectiveWidget from './AffectiveWidget';
import {
    MessageSquare, Brain, Zap, Link2, Key,
    CheckSquare, FolderOpen, Shield, ChevronLeft, ChevronRight, ChevronDown, ChevronUp,
    LayoutList, BarChart3, Calendar, Bot, Settings, ScrollText, Bug, CalendarDays, Wallet, Server, GitFork, Activity
} from 'lucide-react';

interface NavItem {
    id: ActiveView;
    label: string;
    icon: React.FC<any>;
}

interface NavGroup {
    id: string;
    label: string;
    items: NavItem[];
}

const TOP_ITEMS: NavItem[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'sessions', label: 'Sessions', icon: LayoutList },
];

const NAV_GROUPS: NavGroup[] = [
    {
        id: 'control',
        label: 'Control',
        items: [
            { id: 'config', label: 'Config', icon: Settings },
            { id: 'wallet', label: 'Wallet', icon: Wallet },
            { id: 'node', label: 'Node', icon: Server },
            { id: 'bridges', label: 'Bridges', icon: Link2 },
            { id: 'api', label: 'API', icon: Key },
        ]
    },
    {
        id: 'workforce',
        label: 'Workforce',
        items: [
            { id: 'soul', label: 'Soul', icon: Brain },
            { id: 'skills', label: 'Skills', icon: Zap },
            { id: 'memory', label: 'Memory', icon: FolderOpen },
            { id: 'agents', label: 'Agents', icon: Bot },
        ]
    },
    {
        id: 'actions',
        label: 'Actions',
        items: [
            { id: 'crons', label: 'Crons', icon: CalendarDays },
            { id: 'tasks', label: 'Tasks', icon: CheckSquare },
            { id: 'dag', label: 'DAG Planner', icon: GitFork },
        ]
    },
    {
        id: 'monitoring',
        label: 'Monitoring',
        items: [
            { id: 'analytics', label: 'Usage', icon: BarChart3 },
            { id: 'pvt', label: 'PVT', icon: Activity },
            { id: 'audit', label: 'Audit', icon: Shield },
            { id: 'logs', label: 'Logs', icon: ScrollText },
            { id: 'debug', label: 'Debug', icon: Bug },
        ]
    }
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

    const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

    const toggleGroup = (groupId: string) => {
        setCollapsedGroups(prev => ({
            ...prev,
            [groupId]: !prev[groupId]
        }));
    };

    return (
        <aside
            className={`sidebar ${isSidebarCollapsed ? 'sidebar--collapsed' : ''} flex flex-col`}
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
            <nav className="sidebar__nav flex-1 overflow-y-auto overflow-x-hidden pb-4" style={{ paddingRight: isSidebarCollapsed ? 0 : '12px' }}>
                <div className="flex flex-col gap-1">
                    {TOP_ITEMS.map(item => {
                        const Icon = item.icon;
                        const isActive = activeView === item.id;
                        return (
                            <button
                                key={item.id}
                                onClick={() => setActiveView(item.id)}
                                className={`sidebar__item ${isActive ? 'sidebar__item--active' : ''} `}
                                title={isSidebarCollapsed ? item.label : undefined}
                            >
                                <Icon size={18} strokeWidth={isActive ? 2.2 : 1.6} />
                                {!isSidebarCollapsed && (
                                    <span className="sidebar__item-label">{item.label}</span>
                                )}
                            </button>
                        );
                    })}
                </div>

                {NAV_GROUPS.map(group => {
                    const isCollapsed = collapsedGroups[group.id];
                    return (
                        <div key={group.id} className="mt-4 flex flex-col gap-1">
                            {!isSidebarCollapsed && (
                                <button
                                    onClick={() => toggleGroup(group.id)}
                                    className="flex items-center justify-between px-3 py-1 text-[10px] font-mono tracking-widest uppercase text-text-tertiary hover:text-text-secondary transition-colors"
                                >
                                    <span>{group.label}</span>
                                    {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                                </button>
                            )}

                            {(!isCollapsed || isSidebarCollapsed) && group.items.map(item => {
                                const Icon = item.icon;
                                const isActive = activeView === item.id;
                                return (
                                    <button
                                        key={item.id}
                                        onClick={() => setActiveView(item.id)}
                                        className={`sidebar__item ${isActive ? 'sidebar__item--active' : ''} `}
                                        title={isSidebarCollapsed ? item.label : undefined}
                                    >
                                        <Icon size={18} strokeWidth={isActive ? 2.2 : 1.6} />
                                        {!isSidebarCollapsed && (
                                            <span className="sidebar__item-label">{item.label}</span>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    );
                })}
            </nav>

            {/* Affective Engine widget at bottom */}
            {!isSidebarCollapsed && (
                <div className="flex-shrink-0">
                    <AffectiveWidget
                        audioStream={audioStream}
                        videoRef={videoRef}
                        isCameraActive={isCameraActive}
                        toggleCamera={toggleCamera}
                        bridgeManagerRef={bridgeManagerRef}
                        accentColor={accentColor}
                    />
                </div>
            )}
        </aside>
    );
};

export default Sidebar;
