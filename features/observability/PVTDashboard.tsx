import React from 'react';
import { useStore } from '../../store/useStore';
import './pvt-dashboard.css';

interface GaugeProps {
    label: string;
    value: number;
    description: string;
    color: string;
    warningColor: string;
    threshold: number;
    reverse?: boolean;
}

const Gauge: React.FC<GaugeProps> = ({ label, value, description, color, warningColor, threshold, reverse }) => {
    const isWarning = reverse ? value < threshold : value > threshold;
    const activeColor = isWarning ? warningColor : color;
    const percentage = Math.min(100, Math.max(0, value * 100));
    const circumference = 2 * Math.PI * 54;
    const strokeDashoffset = circumference - (circumference * percentage / 100);

    return (
        <div className="pvt-gauge">
            <div className="pvt-gauge__ring">
                <svg viewBox="0 0 120 120">
                    {/* Background track */}
                    <circle
                        cx="60" cy="60" r="54"
                        fill="none"
                        stroke="var(--glass-border)"
                        strokeWidth="6"
                        opacity="0.3"
                    />
                    {/* Value arc */}
                    <circle
                        cx="60" cy="60" r="54"
                        fill="none"
                        stroke={activeColor}
                        strokeWidth="6"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        transform="rotate(-90 60 60)"
                        className="pvt-gauge__arc"
                        style={{
                            filter: `drop-shadow(0 0 6px ${activeColor})`
                        }}
                    />
                </svg>
                <div className="pvt-gauge__value" style={{ color: activeColor }}>
                    {(value * 100).toFixed(1)}
                </div>
            </div>
            <div className="pvt-gauge__label">{label}</div>
            <div className="pvt-gauge__desc">{description}</div>
        </div>
    );
};

interface PsiIndicatorProps {
    value: number;
    isRuptured: boolean;
}

const PsiIndicator: React.FC<PsiIndicatorProps> = ({ value, isRuptured }) => {
    const psiInt = Math.round(value * 1024);
    const hue = Math.max(0, 120 - (value * 120)); // green → red
    const color = `hsl(${hue}, 80%, 55%)`;

    return (
        <div className={`pvt-psi ${isRuptured ? 'pvt-psi--ruptured' : ''}`}>
            <div className="pvt-psi__ring" style={{ borderColor: color, boxShadow: `0 0 20px ${color}40` }}>
                <span className="pvt-psi__label">ψ</span>
                <span className="pvt-psi__value" style={{ color }}>{psiInt}</span>
                <span className="pvt-psi__unit">/1024</span>
            </div>
            <div className="pvt-psi__text">Affective Tension</div>
        </div>
    );
};

const PVTDashboard: React.FC = () => {
    const { pvtHealth } = useStore();
    const { P, V, T, psi, coherence, status, isRuptured, phi_total } = pvtHealth;

    return (
        <div className={`pvt-dashboard ${isRuptured ? 'pvt-dashboard--ruptured' : ''}`}>
            <div className="pvt-dashboard__header">
                <h2>PVT Manifold Health</h2>
                <div className="pvt-dashboard__subtitle">Pressure · Volume · Temperature</div>
            </div>

            {/* Status Badge */}
            <div className={`pvt-status pvt-status--${status.toLowerCase()}`}>
                <span className="pvt-status__dot" />
                <span className="pvt-status__text">{status}</span>
                {phi_total > 0 && (
                    <span className="pvt-status__phi">Φ = {phi_total}</span>
                )}
            </div>

            {/* Gauge Grid */}
            <div className="pvt-grid">
                <Gauge
                    label="Manifold Pressure"
                    value={P}
                    description="Constraint density / admissible volume"
                    color="var(--color-success)"
                    warningColor="var(--color-error)"
                    threshold={0.8}
                />
                <Gauge
                    label="Agency Volume"
                    value={V}
                    description="Hyper-volume of admissible set C_N"
                    color="var(--color-success)"
                    warningColor="var(--color-warning)"
                    threshold={0.3}
                    reverse
                />
                <Gauge
                    label="Topological Temp"
                    value={T}
                    description="Structural entropy / Betti stability"
                    color="var(--color-info)"
                    warningColor="var(--color-warning)"
                    threshold={0.5}
                />
            </div>

            {/* Central ψ Indicator */}
            <PsiIndicator value={psi} isRuptured={isRuptured} />

            {/* Metrics Footer */}
            <div className="pvt-metrics">
                <div className="pvt-metric">
                    <span className="pvt-metric__label">Coherence</span>
                    <span className="pvt-metric__value">{(coherence * 100).toFixed(1)}%</span>
                </div>
                <div className="pvt-metric">
                    <span className="pvt-metric__label">P</span>
                    <span className="pvt-metric__value">{P.toFixed(4)}</span>
                </div>
                <div className="pvt-metric">
                    <span className="pvt-metric__label">V</span>
                    <span className="pvt-metric__value">{V.toFixed(4)}</span>
                </div>
                <div className="pvt-metric">
                    <span className="pvt-metric__label">T</span>
                    <span className="pvt-metric__value">{T.toFixed(4)}</span>
                </div>
            </div>

            {/* Rupture Overlay */}
            {isRuptured && (
                <div className="pvt-rupture-overlay">
                    <div className="pvt-rupture-overlay__content">
                        <div className="pvt-rupture-overlay__icon">⚠</div>
                        <h3>Manifold Rupture</h3>
                        <p>Topological entropy exceeds threshold — g=0 Safe-Halt engaged</p>
                        <div className="pvt-rupture-overlay__values">
                            T = {T.toFixed(4)} &gt; {0.8}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PVTDashboard;
