import React from 'react';
import styles from './NetworkEgressStep.module.css';

interface NetworkEgressProps {
  hosts: string[];
  setHosts: (hosts: string[]) => void;
  rotation: { interval_days: number; last_rotated: string | null };
  setRotation: (r: any) => void;
}

export const NetworkEgressStep: React.FC<NetworkEgressProps> = ({ hosts, setHosts, rotation, setRotation }) => (
  <div className={styles.container}>
    <div className={styles.container}>
      <label className={styles.label}>Allowed Egress Hosts</label>
      <div className={styles.hostsWrapper}>
        {hosts.map((host, i) => (
          <div key={i} className={styles.hostChip}>
            {host}
            <button onClick={() => setHosts(hosts.filter((_, idx) => idx !== i))}>✕</button>
          </div>
        ))}
      </div>
    </div>
    <div className={styles.container}>
      <label className={styles.label}>Rotation Interval (Days)</label>
      <input
        type="number"
        value={rotation.interval_days}
        onChange={e => setRotation({ ...rotation, interval_days: parseInt(e.target.value) })}
        className={styles.input}
      />
    </div>
  </div>
);
