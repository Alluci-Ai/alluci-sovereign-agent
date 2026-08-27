---
description: Run automated tests with coverage and failure diagnostics
agent: codi
---

Run the test suite using pytest or npm test as appropriate for the workspace:
!`./.venv/bin/pytest -v`

Focus on failing tests, run compiler/AST diagnostics on affected modules, and provide surgical fixes without mocks or stubs.
