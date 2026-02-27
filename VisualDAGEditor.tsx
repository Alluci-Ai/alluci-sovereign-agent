
import React, { useState, useEffect, useRef } from 'react';
import { ExecutionGraph, GraphNode, GraphEdge } from './types';

interface VisualDAGEditorProps {
  items: string[];
  graph?: ExecutionGraph;
  onChange: (graph: ExecutionGraph) => void;
}

const VisualDAGEditor: React.FC<VisualDAGEditorProps> = ({ items, graph, onChange }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const [linkingNode, setLinkingNode] = useState<string | null>(null); // Node ID we are dragging a link FROM
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Sync nodes with items (Knowledge Domains)
  useEffect(() => {
    const currentGraphNodes = graph?.nodes || [];
    const currentGraphEdges = graph?.edges || [];
    
    // Create nodes for items that don't exist yet
    const newNodes = items.map((item, index) => {
      const existing = currentGraphNodes.find(n => n.id === item);
      if (existing) return existing;
      
      // Auto-layout new nodes
      return {
        id: item,
        x: 50 + (index % 3) * 160,
        y: 50 + Math.floor(index / 3) * 100
      };
    });

    // Remove nodes that are no longer in items
    const filteredNodes = newNodes.filter(n => items.includes(n.id));
    
    // Clean edges for removed nodes
    const filteredEdges = currentGraphEdges.filter(e => 
      items.includes(e.source) && items.includes(e.target)
    );

    setNodes(filteredNodes);
    setEdges(filteredEdges);
  }, [items]); 

  // DFS Cycle Detection
  const detectCycle = (newEdges: GraphEdge[]) => {
    const adj = new Map<string, string[]>();
    newEdges.forEach(e => {
        if (!adj.has(e.source)) adj.set(e.source, []);
        adj.get(e.source)!.push(e.target);
    });
    
    const visited = new Set<string>();
    const recStack = new Set<string>();
    
    const isCyclic = (v: string): boolean => {
        visited.add(v);
        recStack.add(v);
        const neighbors = adj.get(v) || [];
        for (const neighbor of neighbors) {
            if (!visited.has(neighbor)) {
                if (isCyclic(neighbor)) return true;
            } else if (recStack.has(neighbor)) {
                return true;
            }
        }
        recStack.delete(v);
        return false;
    };
    
    for (const node of nodes) {
        if (!visited.has(node.id)) {
            if (isCyclic(node.id)) return true;
        }
    }
    return false;
  };

  const handleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    if (e.shiftKey) {
      setLinkingNode(nodeId);
    } else {
      setDraggedNode(nodeId);
    }
  };

  // Dedicated handler for connector dots to start linking without Shift
  const handleConnectorMouseDown = (e: React.MouseEvent, nodeId: string) => {
      e.stopPropagation();
      setLinkingNode(nodeId);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setMousePos({ x, y });

    if (draggedNode) {
      const newNodes = nodes.map(n => n.id === draggedNode ? { ...n, x: x - 60, y: y - 20 } : n);
      setNodes(newNodes);
    }
  };

  const handleMouseUp = (e: React.MouseEvent, targetNodeId?: string) => {
    if (linkingNode && targetNodeId && linkingNode !== targetNodeId) {
      const exists = edges.find(edge => edge.source === linkingNode && edge.target === targetNodeId);
      if (!exists) {
        const potentialEdges = [...edges, { source: linkingNode, target: targetNodeId }];
        if (!detectCycle(potentialEdges)) {
            setEdges(potentialEdges);
            onChange({ nodes, edges: potentialEdges });
        } else {
            console.warn("Cycle detected, ignoring edge.");
        }
      }
    } else if (draggedNode) {
      // Finalize drag
      onChange({ nodes, edges });
    }

    setDraggedNode(null);
    setLinkingNode(null);
  };

  const removeEdge = (index: number) => {
    const newEdges = edges.filter((_, i) => i !== index);
    setEdges(newEdges);
    onChange({ nodes, edges: newEdges });
  };

  return (
    <div 
      ref={containerRef}
      className="w-full h-full bg-zinc/5 relative overflow-hidden select-none"
      onMouseMove={handleMouseMove}
      onMouseUp={(e) => handleMouseUp(e)}
      onMouseLeave={() => { setDraggedNode(null); setLinkingNode(null); }}
    >
      <div className="absolute top-2 left-2 text-[7px] font-mono opacity-40 pointer-events-none z-0">
        DAG_TOPOLOGY_EDITOR<br/>
        DRAG from dots to Connect<br/>
        DRAG node to Move<br/>
        DOUBLE_CLICK Edge to Delete
      </div>

      <div className="absolute inset-0 opacity-10 pointer-events-none" 
           style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '20px 20px' }} />

      <svg className="absolute inset-0 w-full h-full overflow-visible pointer-events-auto">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#000" />
          </marker>
        </defs>

        {edges.map((edge, i) => {
          const source = nodes.find(n => n.id === edge.source);
          const target = nodes.find(n => n.id === edge.target);
          if (!source || !target) return null;

          const sx = source.x + 60; 
          const sy = source.y + 40; 
          const tx = target.x + 60; 
          const ty = target.y;      

          const d = `M ${sx} ${sy} C ${sx} ${sy + 50}, ${tx} ${ty - 50}, ${tx} ${ty}`;

          return (
            <g key={i} className="group cursor-pointer" onDoubleClick={() => removeEdge(i)}>
              {/* Thick invisible path for easier hit detection */}
              <path d={d} fill="none" stroke="transparent" strokeWidth="15" />
              {/* Visible path */}
              <path d={d} fill="none" stroke="#000" strokeWidth="1.5" markerEnd="url(#arrowhead)" className="group-hover:stroke-tension group-hover:stroke-2 transition-colors" />
            </g>
          );
        })}

        {linkingNode && (
          <path 
            d={`M ${nodes.find(n => n.id === linkingNode)!.x + 60} ${nodes.find(n => n.id === linkingNode)!.y + 40} L ${mousePos.x} ${mousePos.y}`}
            fill="none" 
            stroke="#91D65F" 
            strokeWidth="1.5" 
            strokeDasharray="4"
          />
        )}
      </svg>

      {nodes.map(node => (
        <div
          key={node.id}
          className={`absolute flex flex-col items-center justify-center w-[120px] h-[40px] bg-white border transition-all z-10 group ${linkingNode === node.id ? 'border-agent shadow-[0_0_10px_rgba(145,214,95,0.3)]' : 'border-zinc/30 hover:border-black'}`}
          style={{ 
            left: node.x, 
            top: node.y,
            boxShadow: '0 4px 6px rgba(0,0,0,0.02)'
          }}
          onMouseDown={(e) => handleMouseDown(e, node.id)}
          onMouseUp={(e) => handleMouseUp(e, node.id)}
        >
          <span className="baunk-style text-[8px] truncate max-w-[90%] pointer-events-none select-none">{node.id}</span>
          
          {/* Connector Handle - Bottom (Source) */}
          <div 
            className="absolute -bottom-2 w-4 h-4 rounded-full flex items-center justify-center cursor-crosshair opacity-0 group-hover:opacity-100 transition-opacity"
            onMouseDown={(e) => handleConnectorMouseDown(e, node.id)}
          >
             <div className="w-2 h-2 bg-black rounded-full hover:bg-agent hover:scale-125 transition-all" />
          </div>

           {/* Connector Handle - Top (Target) - Visual only, for dropping */}
           <div className="absolute -top-2 w-4 h-4 rounded-full flex items-center justify-center pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
             <div className="w-1.5 h-1.5 border border-black rounded-full bg-white" />
          </div>
        </div>
      ))}
    </div>
  );
};

export default VisualDAGEditor;
