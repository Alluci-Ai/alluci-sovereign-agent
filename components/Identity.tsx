import React from 'react';

export const PolytopeIdentity: React.FC<{ color?: string; size?: number; active?: boolean }> = ({ color = "#91D65F", size = 48, active }) => {
    return (
        <svg width={size} height={size} viewBox="0 0 100 100" fill="none" className={`transition-all duration-700 ${active ? 'scale-110 drop-shadow-[0_0_12px_rgba(145,214,95,0.4)]' : 'scale-100 opacity-60'}`}>
            <defs>
                <filter id='glow'>
                    <feGaussianBlur stdDeviation='4' result='blur' />
                    <feMerge><feMergeNode in='blur' /><feMergeNode in='SourceGraphic' /></feMerge>
                </filter>
            </defs>
            <g filter={active ? 'url(#glow)' : undefined}>
                <path d="M11 26L89 8L45 42L11 26Z" fill={color} fillOpacity="1" />
                <path d="M89 8L74 92L45 42L89 8Z" fill={color} fillOpacity="0.8" />
                <path d="M74 92L11 26L45 42L74 92Z" fill={color} fillOpacity="0.6" />
            </g>
        </svg>
    );
};

export default PolytopeIdentity;
