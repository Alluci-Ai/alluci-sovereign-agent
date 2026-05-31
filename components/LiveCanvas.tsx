
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useMemo } from 'react';
import { Layout, Maximize2, MousePointer2, Layers } from 'lucide-react';

export interface CanvasNode {
    id: string;
    type: 'TEXT' | 'IMAGE' | 'DATA';
    content: string;
    x: number;
    y: number;
}

interface LiveCanvasProps {
    nodes: CanvasNode[];
    onNodeMove?: (id: string, x: number, y: number) => void;
}

/**
 * [ LIVE_CANVAS_A2UI ]
 * Agent-to-User Interface (A2UI) visual workspace.
 * Allows agents to "manifest" results as interactive spatial nodes.
 */
const LiveCanvas: React.FC<LiveCanvasProps> = ({ nodes }) => {
    return (
        <div className="relative w-full h-full bg-[#fdfdfd] sovereign-grid overflow-hidden border border-zinc/10 rounded-sm">
            {/* Canvas Header */}
            <div className="flex flex-col h-full bg-white relative">
                <div className="flex items-center gap-2 px-2 py-1 bg-black text-white rounded-xs">
                    <Layers size={14} />
                    <span className="glass-label text-[9px] tracking-widest">A2UI_CANVAS</span>
                </div>
                <div className="flex gap-2 text-secondary/40">
                    <MousePointer2 size={14} />
                    <Layout size={14} />
                    <Maximize2 size={14} />
                </div>
            </div>

            {/* Spatial Nodes */}
            <div className="absolute inset-0 p-8">
                {nodes.map(node => (
                    <div
                        key={node.id}
                        className="absolute p-4 glass-card bg-glass-1 backdrop-blur-md shadow-xl cursor-move hover:shadow-2xl hover:scale-[1.02] transition-all"
                        style={{ left: node.x, top: node.y, maxWidth: '300px' }}
                    >
                        <div className="flex justify-between items-center mb-2 border-b border-black/5 pb-1">
                            <span className="text-[7px] glass-label opacity-30">{node.type}_PRIMARY_OUTPUT</span>
                            <div className="w-1.5 h-1.5 rounded-full bg-agent animate-pulse" />
                        </div>
                        {node.type === 'IMAGE' ? (
                            <img src={node.content} alt="Canvas Manifest" className="w-full h-auto grayscale hover:grayscale-0 transition-all rounded-xs" />
                        ) : (
                            <p className="text-[10px] font-mono leading-relaxed opacity-80">{node.content}</p>
                        )}
                    </div>
                ))}
            </div>

            {/* Background Grid Accent */}
            <div className="absolute bottom-4 right-4 text-[7px] font-mono opacity-10 glass-label">
                COORDINATE_SYSTEM: SIMPLICIAL_SPACE_V1
            </div>
        </div>
    );
};

export default LiveCanvas;
