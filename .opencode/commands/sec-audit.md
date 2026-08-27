---
description: Security audit for hardcoded secrets, dangerous OS calls, and permission violations
agent: codi
---

Audit recent changes and modified files for security vulnerabilities:
Target file/module: $ARGUMENTS

Check for:
1. Secret leakage or unencrypted sensitive fields.
2. Unsanctioned process execution or unsanctioned service restarts.
3. Proper HITL gating for critical financial or filesystem operations.
