
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
        <div className="relative w-full h-full bg-[#fdfdfd] simplicial-grid overflow-hidden border border-zinc/10 rounded-sm">
            {/* Canvas Header */}
            <div className="absolute top-4 left-4 z-10 flex items-center gap-4 bg-white/80 backdrop-blur-md p-2 border border-black/5 rounded-sm shadow-sm">
                <div className="flex items-center gap-2 px-2 py-1 bg-black text-white rounded-xs">
                    <Layers size={14} />
                    <span className="baunk-style text-[9px] tracking-widest">A2UI_CANVAS</span>
                </div>
                <div className="flex gap-2 text-zinc/40">
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
                        className="absolute p-4 bg-white border border-black/10 shadow-lg animate-in zoom-in duration-500 scale-95 hover:scale-100 transition-transform cursor-grab active:cursor-grabbing"
                        style={{ left: node.x, top: node.y, maxWidth: '300px' }}
                    >
                        <div className="flex justify-between items-center mb-2 border-b border-black/5 pb-1">
                            <span className="text-[7px] baunk-style opacity-30">{node.type}_PRIMARY_OUTPUT</span>
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
            <div className="absolute bottom-4 right-4 text-[7px] font-mono opacity-10 baunk-style">
                COORDINATE_SYSTEM: SIMPLICIAL_SPACE_V1
            </div>
        </div>
    );
};

export default LiveCanvas;
