import React, { useState, useEffect } from 'react';
import { Globe, Check } from 'lucide-react';

const LOCALES = [
    { id: 'en', name: 'English', verified: true },
    { id: 'zh-CN', name: '简体中文', verified: false },
    { id: 'zh-TW', name: '繁體中文', verified: false },
    { id: 'pt-BR', name: 'Português (Brasil)', verified: false },
    { id: 'de', name: 'Deutsch', verified: false }
];

// Simple Translation Hook logic stub mirroring i18n
export const useTranslation = () => {
    const locale = localStorage.getItem('OS_LOCALE') || 'en';
    const t = (key: string, _defaultVal?: string) => {
        // Mock fallback to default strings natively evaluating english bundles
        return _defaultVal || key;
    };
    return { t, locale };
};

export const LocaleSelector: React.FC = () => {
    const [savedLocale, setSavedLocale] = useState(() => localStorage.getItem('OS_LOCALE') || 'en');
    const [isOpen, setIsOpen] = useState(false);

    const changeLocale = (id: string) => {
        localStorage.setItem('OS_LOCALE', id);
        setSavedLocale(id);
        setIsOpen(false);
        // Dispatch event or just let standard reloads catch state
    };

    return (
        <div className="bg-glass-1 border border-glass-edge p-5 rounded-xl flex flex-col gap-4 relative">
            <div className="flex items-center justify-between border-b border-glass-edge pb-3">
                <h3 className="text-xs font-medium tracking-tight flex items-center gap-2">
                    <Globe size={14} className="text-accent" /> i18n Native Bundles
                </h3>
            </div>

            <p className="text-[10px] text-text-tertiary leading-relaxed mb-1">
                Select the primary linguistics engine rendering. Non-english bundles are sourced by open-source community validators.
            </p>

            <div className="relative">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="w-full flex items-center justify-between glass-input text-xs text-left"
                >
                    <span>{LOCALES.find(l => l.id === savedLocale)?.name || 'English'} ({savedLocale})</span>
                    <span className="opacity-40 text-[10px]">▼</span>
                </button>

                {isOpen && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-glass-1 border border-glass-edge rounded-lg shadow-xl shadow-black/40 overflow-hidden z-20 animate-in fade-in duration-200">
                        {LOCALES.map(loc => (
                            <button
                                key={loc.id}
                                onClick={() => changeLocale(loc.id)}
                                className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors text-left hover:bg-white/5 ${savedLocale === loc.id ? 'bg-glass-pressed text-accent' : 'text-text-secondary'}`}
                            >
                                <span className="flex items-center gap-2">
                                    {loc.name}
                                    {!loc.verified && <span className="text-[8px] font-mono opacity-50 border border-current px-1 rounded uppercase">Community</span>}
                                </span>
                                {savedLocale === loc.id && <Check size={12} />}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default LocaleSelector;
