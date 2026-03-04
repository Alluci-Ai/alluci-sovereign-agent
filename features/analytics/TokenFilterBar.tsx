import React, { useState } from 'react';
import { Search, X } from 'lucide-react';

export interface TokenFilterState {
    query: string;
    model?: string;
    minTokens?: number;
}

interface TokenFilterBarProps {
    onFilterChange: (filters: TokenFilterState) => void;
}

export const TokenFilterBar: React.FC<TokenFilterBarProps> = ({ onFilterChange }) => {
    const [query, setQuery] = useState('');
    const [model, setModel] = useState<string>('');
    const [minTokens, setMinTokens] = useState<number | ''>('');

    const applyFilters = (newQuery: string, newModel: string, newTokens: number | '') => {
        onFilterChange({
            query: newQuery,
            model: newModel || undefined,
            minTokens: typeof newTokens === 'number' ? newTokens : undefined
        });
    };

    return (
        <div className="flex flex-wrap items-center gap-3 bg-glass-1 border border-glass-edge rounded-xl p-3 backdrop-blur-md">
            <div className="flex items-center gap-2 flex-1 min-w-[200px] border border-glass-edge rounded-lg px-3 py-1.5 focus-within:border-accent transition-colors bg-glass-2">
                <Search size={14} className="text-text-secondary" />
                <input
                    type="text"
                    placeholder="Search by session key..."
                    value={query}
                    onChange={e => {
                        setQuery(e.target.value);
                        applyFilters(e.target.value, model, minTokens);
                    }}
                    className="bg-transparent border-none text-xs text-text-primary focus:outline-none w-full"
                />
            </div>

            <div className="flex items-center gap-2">
                <select
                    value={model}
                    onChange={e => {
                        setModel(e.target.value);
                        applyFilters(query, e.target.value, minTokens);
                    }}
                    className="glass-input text-xs w-32"
                >
                    <option value="">All Models</option>
                    <option value="gemini-1.5-pro">Gemini Pro</option>
                    <option value="gemini-1.5-flash">Gemini Flash</option>
                    <option value="claude-3-5-sonnet">Claude 3.5</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="deepseek-chat">DeepSeek</option>
                </select>

                <input
                    type="number"
                    placeholder="Min Tokens"
                    value={minTokens}
                    onChange={e => {
                        const val = e.target.value === '' ? '' : parseInt(e.target.value);
                        setMinTokens(val);
                        applyFilters(query, model, val);
                    }}
                    className="glass-input text-xs w-28"
                    min="0"
                />

                {(query || model || minTokens !== '') && (
                    <button
                        onClick={() => {
                            setQuery('');
                            setModel('');
                            setMinTokens('');
                            applyFilters('', '', '');
                        }}
                        className="p-1.5 hover:bg-glass-edge rounded-full transition-colors text-text-secondary hover:text-text-primary"
                        title="Clear filters"
                    >
                        <X size={14} />
                    </button>
                )}
            </div>
        </div>
    );
};

export default TokenFilterBar;
