// frontend/src/components/AdvancedSettings.tsx
import React, { useEffect, useState } from "react";

/**
 * Advanced Settings tab – allows the user to control MAX_CONCURRENCY.
 * Styled with glassmorphism and dark‑mode friendly aesthetics.
 */
const AdvancedSettings: React.FC = () => {
  const [maxConcurrency, setMaxConcurrency] = useState<number>(4);
  const [loading, setLoading] = useState<boolean>(true);

  // Fetch current config on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch("/api/v1/config");
        const data = await res.json();
        const value = data.max_concurrency ?? 4;
        setMaxConcurrency(value);
      } catch (e) {
        console.error("Failed to load config", e);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async () => {
    try {
      await fetch("/api/v1/config", {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ max_concurrency: maxConcurrency })
});
      alert("Configuration saved!");
    } catch (e) {
      console.error(e);
      alert("Failed to save configuration");
    }
  };

  if (loading) return <div>Loading…</div>;

  return (
    <section className="advanced-settings glass-card">
      <h2 className="title">Advanced Settings</h2>
      <label htmlFor="max-concurrency" className="label">
        Max Concurrency (LLM inference workers)
      </label>
      <input
        id="max-concurrency"
        type="range"
        min={1}
        max={64}
        step={1}
        value={maxConcurrency}
        onChange={e => setMaxConcurrency(Number(e.target.value))}
        className="slider"
      />
      <output className="value-display">{maxConcurrency}</output>
      <button onClick={handleSave} className="save-button">
        Save
      </button>
    </section>
  );
};

export default AdvancedSettings;
