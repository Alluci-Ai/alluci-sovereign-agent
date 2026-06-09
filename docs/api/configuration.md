# API Configuration Schema

All configuration fields are exposed via the `/api/v1/config` endpoint (GET and PUT).

## Fields

- **max_concurrency** *(int, default: 5)* – Controls the maximum number of concurrent inference workers. The UI exposes this as a slider (1‑64) in **Advanced Settings**.
- **MAX_CONCURRENT_TASKS** – Internal task queue limit (unchanged).
- **SOVEREIGN_MODE** – When `true`, all cloud providers are disabled.
- **...** – Existing fields remain unchanged.

When an API key for a cloud provider is missing, the corresponding provider is **silently disabled** and a debug log entry is emitted. No error is raised, allowing the test suite and CI pipelines to run without external credentials.
