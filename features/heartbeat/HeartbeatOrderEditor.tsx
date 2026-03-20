/**
 * HeartbeatOrderEditor
 * =====================
 * Reusable structured heartbeat order editor.
 * Used in:
 *   1. SoulPreferencesPanel (root agent orders)
 *   2. AgentDetailTabs > Heartbeat tab (per-agent orders)
 *
 * Renders a list of structured orders with enable/disable toggles,
 * an "Add Order" form with probe type and action type selectors,
 * last-fired timestamp per order, and outcome badges.
 */
import React, { useState, useCallback } from 'react';
import { Plus, Trash2, Play, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export interface HeartbeatOrder {
  id: string;
  label: string;
  active: boolean;
  probe_type: ProbeType;
  probe_config: Record<string, any>;
  action_type: ActionType;
  action_config: Record<string, any>;
  interval_minutes: number;
  last_fired?: number;
  last_outcome?: 'success' | 'failed' | 'skipped' | 'no_change';
}

type ProbeType =
  | 'file_watch' | 'task_deadline' | 'goal_progress'
  | 'url_fetch' | 'memory_pattern' | 'system_health'
  | 'bridge_silence' | 'cron_expression';

type ActionType =
  | 'notify_ws' | 'notify_bridge' | 'execute_objective'
  | 'evaluate_goal' | 'log_only' | 'pcl_signal';

const PROBE_LABELS: Record<ProbeType, string> = {
  file_watch:       'File Watch',
  task_deadline:    'Task Deadline',
  goal_progress:    'Goal Progress',
  url_fetch:        'URL Fetch',
  memory_pattern:   'Memory Pattern',
  system_health:    'System Health',
  bridge_silence:   'Bridge Silence',
  cron_expression:  'Cron Schedule',
};

const ACTION_LABELS: Record<ActionType, string> = {
  notify_ws:          'Notify UI',
  notify_bridge:      'Notify via Bridge',
  execute_objective:  'Execute Objective',
  evaluate_goal:      'Evaluate Goal',
  log_only:           'Log Only',
  pcl_signal:         'Feed to PCL',
};

const ACTION_COLORS: Record<ActionType, string> = {
  notify_ws:          'text-yellow-400',
  notify_bridge:      'text-blue-400',
  execute_objective:  'text-red-400',
  evaluate_goal:      'text-emerald-400',
  log_only:           'text-text-muted',
  pcl_signal:         'text-purple-400',
};

const OUTCOME_ICON = {
  success:   <CheckCircle size={10} className="text-emerald-400" />,
  failed:    <XCircle size={10} className="text-red-400" />,
  skipped:   <AlertCircle size={10} className="text-yellow-400" />,
  no_change: <Clock size={10} className="text-text-muted" />,
};

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function makeDefaultOrder(): HeartbeatOrder {
  return {
    id: generateId(),
    label: 'New Order',
    active: true,
    probe_type: 'task_deadline',
    probe_config: { path: 'TASKS.md' },
    action_type: 'notify_ws',
    action_config: { message_template: '{label}: {probe_detail}' },
    interval_minutes: 15,
  };
}

// ── Probe Config Fields ────────────────────────────────────────────────────────

const ProbeConfigFields: React.FC<{
  probeType: ProbeType;
  config: Record<string, any>;
  onChange: (cfg: Record<string, any>) => void;
}> = ({ probeType, config, onChange }) => {
  const field = (key: string, label: string, placeholder = '') => (
    <div key={key} className="flex flex-col gap-1">
      <label className="text-[9px] font-mono text-text-muted uppercase">{label}</label>
      <input
        className="glass-input text-[11px] font-mono py-1 px-2"
        value={config[key] ?? ''}
        onChange={e => onChange({ ...config, [key]: e.target.value })}
        placeholder={placeholder}
      />
    </div>
  );

  switch (probeType) {
    case 'file_watch':
      return field('path', 'File / Directory Path', 'TASKS.md');
    case 'task_deadline':
      return (
        <div className="flex gap-2">
          {field('path', 'Tasks File', 'TASKS.md')}
          {field('threshold_days', 'Overdue Days', '0')}
        </div>
      );
    case 'goal_progress':
      return (
        <div className="flex gap-2">
          {field('goal_id', 'Goal ID', '1')}
          {field('threshold_pct', 'Below % Threshold', '50')}
        </div>
      );
    case 'url_fetch':
      return (
        <div className="flex flex-col gap-2">
          {field('url', 'URL', 'https://...')}
          {field('keyword', 'Keyword (optional)', 'AI agent')}
        </div>
      );
    case 'memory_pattern':
      return (
        <div className="flex gap-2">
          {field('query', 'Search Query', 'deployment issue')}
          {field('min_occurrences', 'Min Times', '2')}
        </div>
      );
    case 'system_health':
      return (
        <div className="flex gap-2">
          {field('failure_threshold', 'Failure Count', '3')}
          {field('hours', 'Lookback Hours', '4')}
        </div>
      );
    case 'bridge_silence':
      return (
        <div className="flex gap-2">
          {field('bridge_id', 'Bridge ID', 'telegram')}
          {field('silence_hours', 'Silence Hours', '4')}
        </div>
      );
    case 'cron_expression':
      return field('expression', 'Cron Expression', '0 9 * * 1-5');
    default:
      return null;
  }
};

// ── Action Config Fields ──────────────────────────────────────────────────────

const ActionConfigFields: React.FC<{
  actionType: ActionType;
  config: Record<string, any>;
  onChange: (cfg: Record<string, any>) => void;
}> = ({ actionType, config, onChange }) => {
  const field = (key: string, label: string, placeholder = '') => (
    <div key={key} className="flex flex-col gap-1">
      <label className="text-[9px] font-mono text-text-muted uppercase">{label}</label>
      <input
        className="glass-input text-[11px] font-mono py-1 px-2"
        value={config[key] ?? ''}
        onChange={e => onChange({ ...config, [key]: e.target.value })}
        placeholder={placeholder}
      />
    </div>
  );

  switch (actionType) {
    case 'notify_ws':
      return field('message_template', 'Message Template', '{label}: {probe_detail}');
    case 'notify_bridge':
      return (
        <div className="flex flex-col gap-2">
          {field('bridge_id', 'Bridge ID', 'telegram')}
          {field('recipient', 'Recipient', '+1234567890')}
          {field('message_template', 'Message Template', '{label}: {probe_detail}')}
        </div>
      );
    case 'execute_objective':
      return (
        <div className="flex flex-col gap-2">
          {field('objective_template', 'Objective Template', '{label}: {probe_detail}')}
          <div className="flex flex-col gap-1">
            <label className="text-[9px] font-mono text-text-muted uppercase">Autonomy Level</label>
            <select
              className="glass-input text-[11px] py-1 px-2"
              value={config.autonomy ?? 'RESTRICTED'}
              onChange={e => onChange({ ...config, autonomy: e.target.value })}
            >
              <option value="RESTRICTED">RESTRICTED</option>
              <option value="SEMI_AUTONOMOUS">SEMI_AUTONOMOUS</option>
            </select>
          </div>
        </div>
      );
    case 'evaluate_goal':
      return field('goal_id', 'Goal ID', '1');
    case 'pcl_signal':
      return (
        <div className="flex gap-2">
          {field('signal_label', 'Signal Label', 'Custom Signal')}
          <div className="flex flex-col gap-1">
            <label className="text-[9px] font-mono text-text-muted uppercase">Priority</label>
            <select
              className="glass-input text-[11px] py-1 px-2"
              value={config.priority ?? 3}
              onChange={e => onChange({ ...config, priority: Number(e.target.value) })}
            >
              {[1, 2, 3, 4, 5].map(p => (
                <option key={p} value={p}>P{p} — {['Critical', 'High', 'Medium', 'Low', 'Minimal'][p - 1]}</option>
              ))}
            </select>
          </div>
        </div>
      );
    case 'log_only':
      return <p className="text-[10px] text-text-muted font-mono">Result written to H-LSM L1 episodic memory. No user-facing action.</p>;
    default:
      return null;
  }
};

// ── Main Component ─────────────────────────────────────────────────────────────

interface HeartbeatOrderEditorProps {
  orders: HeartbeatOrder[];
  onChange: (orders: HeartbeatOrder[]) => void;
  orderHistory?: Record<string, Array<{ fired_at: number; outcome: string; detail: string }>>;
  compact?: boolean;
}

export const HeartbeatOrderEditor: React.FC<HeartbeatOrderEditorProps> = ({
  orders,
  onChange,
  orderHistory = {},
  compact = false,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newOrder, setNewOrder] = useState<HeartbeatOrder>(makeDefaultOrder());

  const toggle = (id: string) => {
    onChange(orders.map(o => o.id === id ? { ...o, active: !o.active } : o));
  };

  const remove = (id: string) => {
    onChange(orders.filter(o => o.id !== id));
  };

  const update = (id: string, patch: Partial<HeartbeatOrder>) => {
    onChange(orders.map(o => o.id === id ? { ...o, ...patch } : o));
  };

  const addOrder = () => {
    onChange([...orders, { ...newOrder, id: generateId() }]);
    setNewOrder(makeDefaultOrder());
    setAdding(false);
  };

  const formatTime = (ts?: number) => {
    if (!ts) return 'Never';
    const d = new Date(ts * 1000);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return `${Math.round(diff)}s ago`;
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Order List */}
      {orders.length === 0 && !adding && (
        <div className="text-center py-6 text-[11px] font-mono text-text-muted opacity-60">
          No heartbeat orders configured. Add one below.
        </div>
      )}

      {orders.map(order => {
        const isExpanded = expandedId === order.id;
        const history = orderHistory[order.id] || [];
        const lastRecord = history[0];
        const OutcomeIcon = lastRecord ? OUTCOME_ICON[lastRecord.outcome as keyof typeof OUTCOME_ICON] : null;

        return (
          <div
            key={order.id}
            className={`border rounded-xl transition-all ${
              order.active
                ? 'border-glass-edge bg-glass-1'
                : 'border-glass-edge/40 bg-glass-2 opacity-60'
            }`}
          >
            {/* Header Row */}
            <div className="flex items-center gap-3 p-3">
              {/* Toggle */}
              <button
                onClick={() => toggle(order.id)}
                className={`w-8 h-4 rounded-full transition-colors flex-shrink-0 relative ${
                  order.active ? 'bg-accent' : 'bg-glass-pressed'
                }`}
              >
                <span className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${
                  order.active ? 'left-[18px]' : 'left-0.5'
                }`} />
              </button>

              {/* Label + type badges */}
              <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : order.id)}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[12px] font-mono text-text-primary truncate">{order.label}</span>
                  <span className="text-[9px] font-mono text-text-muted bg-glass-pressed px-1.5 py-0.5 rounded">
                    {PROBE_LABELS[order.probe_type]}
                  </span>
                  <span className={`text-[9px] font-mono ${ACTION_COLORS[order.action_type]} bg-glass-pressed px-1.5 py-0.5 rounded`}>
                    {ACTION_LABELS[order.action_type]}
                  </span>
                </div>
              </div>

              {/* Last fired + outcome */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {OutcomeIcon}
                <span className="text-[9px] font-mono text-text-muted">
                  {formatTime(lastRecord?.fired_at)}
                </span>
              </div>

              {/* Delete */}
              <button
                onClick={() => remove(order.id)}
                className="text-text-muted hover:text-red-400 transition-colors flex-shrink-0"
              >
                <Trash2 size={12} />
              </button>
            </div>

            {/* Expanded Config */}
            {isExpanded && (
              <div className="border-t border-glass-edge/50 p-3 flex flex-col gap-4">
                {/* Label + Interval */}
                <div className="flex gap-3">
                  <div className="flex flex-col gap-1 flex-1">
                    <label className="text-[9px] font-mono text-text-muted uppercase">Label</label>
                    <input
                      className="glass-input text-[11px] font-mono py-1 px-2"
                      value={order.label}
                      onChange={e => update(order.id, { label: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-1 w-24">
                    <label className="text-[9px] font-mono text-text-muted uppercase">Interval (min)</label>
                    <input
                      type="number"
                      min={1}
                      className="glass-input text-[11px] font-mono py-1 px-2"
                      value={order.interval_minutes}
                      onChange={e => update(order.id, { interval_minutes: Number(e.target.value) })}
                    />
                  </div>
                </div>

                {/* Probe Type + Config */}
                <div className="flex flex-col gap-2">
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] font-mono text-text-muted uppercase">Probe Type</label>
                    <select
                      className="glass-input text-[11px] py-1 px-2"
                      value={order.probe_type}
                      onChange={e => update(order.id, {
                        probe_type: e.target.value as ProbeType,
                        probe_config: {},
                      })}
                    >
                      {(Object.entries(PROBE_LABELS) as [ProbeType, string][]).map(([v, l]) => (
                        <option key={v} value={v}>{l}</option>
                      ))}
                    </select>
                  </div>
                  <ProbeConfigFields
                    probeType={order.probe_type}
                    config={order.probe_config}
                    onChange={cfg => update(order.id, { probe_config: cfg })}
                  />
                </div>

                {/* Action Type + Config */}
                <div className="flex flex-col gap-2">
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] font-mono text-text-muted uppercase">Action Type</label>
                    <select
                      className="glass-input text-[11px] py-1 px-2"
                      value={order.action_type}
                      onChange={e => update(order.id, {
                        action_type: e.target.value as ActionType,
                        action_config: {},
                      })}
                    >
                      {(Object.entries(ACTION_LABELS) as [ActionType, string][]).map(([v, l]) => (
                        <option key={v} value={v}>{l}</option>
                      ))}
                    </select>
                  </div>
                  <ActionConfigFields
                    actionType={order.action_type}
                    config={order.action_config}
                    onChange={cfg => update(order.id, { action_config: cfg })}
                  />
                </div>

                {/* Recent History */}
                {history.length > 0 && (
                  <div className="border-t border-glass-edge/30 pt-2">
                    <p className="text-[9px] font-mono text-text-muted uppercase mb-1.5">Recent History</p>
                    <div className="flex flex-col gap-1">
                      {history.slice(0, 3).map((h, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                          {OUTCOME_ICON[h.outcome as keyof typeof OUTCOME_ICON]}
                          <span className="text-text-muted">{formatTime(h.fired_at)}</span>
                          <span className="text-text-secondary truncate">{h.detail}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Add Order Form */}
      {adding ? (
        <div className="border border-accent/30 rounded-xl p-3 bg-accent/5 flex flex-col gap-3">
          <p className="text-[10px] font-mono text-accent uppercase tracking-widest">New Heartbeat Order</p>

          <div className="flex gap-3">
            <div className="flex flex-col gap-1 flex-1">
              <label className="text-[9px] font-mono text-text-muted uppercase">Label</label>
              <input
                className="glass-input text-[11px] font-mono py-1 px-2"
                value={newOrder.label}
                onChange={e => setNewOrder(o => ({ ...o, label: e.target.value }))}
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-1 w-24">
              <label className="text-[9px] font-mono text-text-muted uppercase">Interval (min)</label>
              <input
                type="number" min={1}
                className="glass-input text-[11px] font-mono py-1 px-2"
                value={newOrder.interval_minutes}
                onChange={e => setNewOrder(o => ({ ...o, interval_minutes: Number(e.target.value) }))}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-[9px] font-mono text-text-muted uppercase">Probe Type</label>
              <select
                className="glass-input text-[11px] py-1 px-2"
                value={newOrder.probe_type}
                onChange={e => setNewOrder(o => ({ ...o, probe_type: e.target.value as ProbeType, probe_config: {} }))}
              >
                {(Object.entries(PROBE_LABELS) as [ProbeType, string][]).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[9px] font-mono text-text-muted uppercase">Action Type</label>
              <select
                className="glass-input text-[11px] py-1 px-2"
                value={newOrder.action_type}
                onChange={e => setNewOrder(o => ({ ...o, action_type: e.target.value as ActionType, action_config: {} }))}
              >
                {(Object.entries(ACTION_LABELS) as [ActionType, string][]).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button onClick={() => setAdding(false)} className="glass-btn text-[11px] px-3 py-1.5">Cancel</button>
            <button
              onClick={addOrder}
              disabled={!newOrder.label.trim()}
              className="glass-btn glass-btn--primary text-[11px] px-4 py-1.5 flex items-center gap-1.5 disabled:opacity-40"
            >
              <Plus size={12} /> Add Order
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="glass-btn w-full text-[11px] font-mono text-text-muted hover:text-accent py-2 border-dashed flex items-center justify-center gap-2"
        >
          <Plus size={12} /> Add Heartbeat Order
        </button>
      )}
    </div>
  );
};
