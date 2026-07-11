import React from 'react';
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react';

export interface JSONSchema {
  type: string;
  properties?: Record<string, JSONSchema>;
  items?: JSONSchema;
  required?: string[];
  description?: string;
}

interface SchemaNodeBuilderProps {
  schema: JSONSchema;
  onChange: (newSchema: JSONSchema) => void;
  isRoot?: boolean;
}

export const SchemaNodeBuilder: React.FC<SchemaNodeBuilderProps> = ({ schema, onChange, isRoot = true }) => {
  const [isExpanded, setIsExpanded] = React.useState(true);

  const handleTypeChange = (newType: string) => {
    const updated: JSONSchema = { ...schema, type: newType };
    if (newType === 'object' && !updated.properties) {
      updated.properties = {};
      updated.required = [];
    } else if (newType === 'array' && !updated.items) {
      updated.items = { type: 'string' };
    }
    onChange(updated);
  };

  const handleDescriptionChange = (desc: string) => {
    onChange({ ...schema, description: desc });
  };

  const handleAddProperty = () => {
    const props = schema.properties || {};
    const newKey = `newProperty${Object.keys(props).length + 1}`;
    onChange({
      ...schema,
      properties: {
        ...props,
        [newKey]: { type: 'string', description: '' }
      }
    });
  };

  const handlePropertyChange = (key: string, newKey: string, newPropSchema: JSONSchema) => {
    const props = { ...schema.properties };
    if (key !== newKey) {
      delete props[key];
    }
    props[newKey] = newPropSchema;
    onChange({ ...schema, properties: props });
  };

  const handleDeleteProperty = (key: string) => {
    const props = { ...schema.properties };
    delete props[key];
    const req = (schema.required || []).filter(r => r !== key);
    onChange({ ...schema, properties: props, required: req });
  };

  const handleToggleRequired = (key: string, isRequired: boolean) => {
    const req = new Set(schema.required || []);
    if (isRequired) req.add(key);
    else req.delete(key);
    onChange({ ...schema, required: Array.from(req) });
  };

  const handleArrayItemsChange = (newItemsSchema: JSONSchema) => {
    onChange({ ...schema, items: newItemsSchema });
  };

  return (
    <div className={`flex flex-col gap-2 ${!isRoot ? 'pl-4 border-l border-glass-edge ml-2 mt-2' : ''}`}>
      <div className="flex items-center gap-2">
        {!isRoot && (schema.type === 'object' || schema.type === 'array') && (
          <button onClick={() => setIsExpanded(!isExpanded)} className="text-text-tertiary hover:text-text-primary">
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        )}
        
        <select 
          value={schema.type || 'string'} 
          onChange={(e) => handleTypeChange(e.target.value)}
          className="bg-glass-pressed border border-glass-edge rounded p-1 text-xs text-text-primary outline-none"
        >
          <option value="string">String</option>
          <option value="number">Number</option>
          <option value="boolean">Boolean</option>
          <option value="object">Object</option>
          <option value="array">Array</option>
        </select>
        
        <input 
          type="text" 
          placeholder="Description (optional)" 
          value={schema.description || ''} 
          onChange={(e) => handleDescriptionChange(e.target.value)}
          className="flex-1 bg-transparent border-b border-glass-edge border-dashed px-2 py-1 text-xs text-text-secondary focus:text-text-primary focus:border-solid outline-none placeholder-text-tertiary"
        />
        
        {schema.type === 'object' && (
          <button onClick={handleAddProperty} className="p-1 hover:bg-glass-3 rounded text-accent transition-colors" title="Add Property">
            <Plus className="w-4 h-4" />
          </button>
        )}
      </div>

      {isExpanded && schema.type === 'object' && schema.properties && (
        <div className="flex flex-col gap-3 mt-2">
          {Object.entries(schema.properties).map(([key, propSchema]) => {
            const isReq = (schema.required || []).includes(key);
            return (
              <div key={key} className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <input 
                    type="text" 
                    value={key} 
                    onChange={(e) => handlePropertyChange(key, e.target.value, propSchema)}
                    className="bg-glass-pressed border border-glass-edge rounded p-1 text-xs text-accent font-mono w-32 outline-none"
                  />
                  <label className="flex items-center gap-1 text-[10px] text-text-tertiary cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={isReq} 
                      onChange={(e) => handleToggleRequired(key, e.target.checked)}
                      className="accent-accent"
                    />
                    Required
                  </label>
                  <button onClick={() => handleDeleteProperty(key)} className="p-1 hover:bg-red-500/20 text-red-400 rounded transition-colors ml-auto">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
                <SchemaNodeBuilder 
                  schema={propSchema} 
                  onChange={(newProp) => handlePropertyChange(key, key, newProp)} 
                  isRoot={false} 
                />
              </div>
            );
          })}
        </div>
      )}

      {isExpanded && schema.type === 'array' && schema.items && (
        <div className="mt-2">
          <div className="text-[10px] uppercase font-mono tracking-widest text-text-tertiary mb-1">Array Items Type</div>
          <SchemaNodeBuilder 
            schema={schema.items} 
            onChange={handleArrayItemsChange} 
            isRoot={false} 
          />
        </div>
      )}
    </div>
  );
};
