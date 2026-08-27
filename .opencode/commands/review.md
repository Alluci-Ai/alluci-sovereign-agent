---
description: Perform AST diffing, non-null contract verification, and zero-stub compliance code review
agent: codi
---

Review the recent modifications across the workspace:
Recent git diff:
!`git diff HEAD~1`

Verify:
1. Zero Stubs, Zero Mocks, and Real End-to-End Wiring Law compliance.
2. Non-null contract safety and defensive error boundaries.
3. Secret isolation (no hardcoded keys, VaultManager usage).
