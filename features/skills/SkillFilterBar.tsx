import React from 'react';
import { Search, Filter, X } from 'lucide-react';

interface SkillFilterBarProps {
    searchQuery: string;
    setSearchQuery: (val: string) => void;
    statusFilter: string;
    setStatusFilter: (val: string) => void;
}

export const SkillFilterBar: React.FC<SkillFilterBarProps> = ({
    searchQuery, setSearchQuery,
    statusFilter, setStatusFilter
}) => {
    return (
        <div className="flex flex-col md:flex-row items-center gap-3 bg-glass-1 border border-glass-edge rounded-xl p-3 shadow-sm relative z-20">
            <div className="relative flex-1 w-full">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" size={16} />
                <input
                    type="text"
                    placeholder="Refine loaded skill matrix..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-glass-pressed border border-white/5 rounded-lg pl-10 pr-4 py-2 text-sm text-text-primary focus:border-accent/40 outline-none transition-colors"
                />
                {searchQuery && (
                    <button
                        onClick={() => setSearchQuery('')}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
                    >
                        <X size={14} />
                    </button>
                )}
            </div>

            <div className="flex items-center gap-2 w-full md:w-auto">
                <Filter size={16} className="text-text-tertiary" />
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-glass-pressed border border-white/5 rounded-lg px-3 py-2 text-sm text-text-secondary outline-none focus:border-accent/40 appearance-none min-w-[120px]"
                >
                    <option value="all">Global Matrix</option>
                    <option value="active">Active Only</option>
                    <option value="error">Failing Links</option>
                </select>
            </div>
        </div>
    );
};

export default SkillFilterBar;
