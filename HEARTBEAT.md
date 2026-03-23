
# Sovereign Agent Standing Orders

This file is read by the `HeartbeatDaemon` every 15 minutes.
Checked items (`- [x]`) are active. Unchecked items (`- [ ]`) are ignored.

NETWORK CONSENT: Orders that make external HTTP requests must include `[NETWORK_OK]`.
Orders WITHOUT this marker that attempt network access will be blocked.

### 1. Project Hygiene
- [ ] Monitor `tasks.md` for changes and suggest prioritization updates.
- [ ] Scan `/logs` for critical error bursts and summarize.

### 2. External Awareness
- [ ] Monitor `https://news.ycombinator.com` for "AI Agent" keywords. (Requires Web Tool)
- [ ] Check `inbox/` directory for new data dumps.

### 3. Autonomy
- [ ] If `tasks.md` has overdue items, draft a proactive Slack message asking for status.
