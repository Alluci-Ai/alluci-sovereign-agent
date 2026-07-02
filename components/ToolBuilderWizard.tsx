import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { ToolManifest } from '../types';
import { Terminal, Save, X, Cpu } from 'lucide-react';

interface ToolBuilderWizardProps {
  onClose: () => void;
}

const ToolBuilderWizard: React.FC<ToolBuilderWizardProps> = ({ onClose }) => {
  const { tools, setTools, toolToEdit } = useStore();

  const [formData, setFormData] = useState<Partial<ToolManifest>>(
    toolToEdit || {
      id: '',
      name: '',
      category: 'TOOL',
      description: '',
      enabled: true,
      params: '{}'
    }
  );

  const handleChange = (field: keyof ToolManifest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    if (!formData.id || !formData.name) return;

    const newTool = formData as ToolManifest;
    
    if (toolToEdit) {
      setTools(prev => prev.map(t => t.id === newTool.id ? newTool : t));
    } else {
      setTools(prev => [...prev, newTool]);
    }
    
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="bg-glass-1 border border-glass-edge rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl relative overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-glass-edge flex items-center justify-between bg-glass-2 relative z-10">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-accent/10 rounded-xl border border-accent/20">
              <Cpu className="text-accent w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-text-primary">
                {toolToEdit ? 'Edit Tool Adapter' : 'Build Native Tool'}
              </h2>
              <p className="text-xs text-text-tertiary mt-1 font-mono uppercase tracking-wider">
                Extrinsic Dependency Configuration
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-glass-3 rounded-xl transition-colors">
            <X className="w-5 h-5 text-text-tertiary" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar relative z-10">
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary flex items-center gap-2">
                Identifier
              </label>
              <input
                type="text"
                value={formData.id}
                onChange={e => handleChange('id', e.target.value)}
                placeholder="e.g., bridge_gmail"
                className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none font-mono"
                disabled={!!toolToEdit}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary flex items-center gap-2">
                Display Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={e => handleChange('name', e.target.value)}
                placeholder="e.g., Gmail Bridge API"
                className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary flex items-center gap-2">
              Category
            </label>
            <select
              value={formData.category}
              onChange={e => handleChange('category', e.target.value)}
              className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none"
            >
              <option value="TOOL">Tool</option>
              <option value="BRIDGE">Bridge</option>
              <option value="MCP">MCP Server</option>
              <option value="CLI">CLI Utility</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary flex items-center gap-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={e => handleChange('description', e.target.value)}
              placeholder="What does this tool do? How should the agent use it?"
              className="w-full bg-glass-pressed border border-glass-edge rounded-xl p-3 text-sm text-text-primary focus:border-accent outline-none h-24 resize-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] uppercase font-mono tracking-widest text-text-secondary flex items-center gap-2">
              <Terminal className="w-3 h-3" /> Default JSON Parameters
            </label>
            <textarea
              value={formData.params}
              onChange={e => handleChange('params', e.target.value)}
              placeholder="{}"
              className="w-full bg-black/40 border border-glass-edge rounded-xl p-4 text-xs text-blue-200 font-mono focus:border-accent outline-none h-32 resize-y"
              spellCheck={false}
            />
          </div>
          
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-glass-edge bg-glass-1/50 flex justify-end gap-3 relative z-10">
          <button 
            onClick={onClose}
            className="px-6 py-2 rounded-xl text-sm font-medium text-text-secondary hover:bg-glass-3 transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            disabled={!formData.id || !formData.name}
            className={`glass-btn glass-btn--primary flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-bold transition-all ${(!formData.id || !formData.name) ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <Save className="w-4 h-4" /> Save Tool
          </button>
        </div>

      </div>
    </div>
  );
};

export default ToolBuilderWizard;