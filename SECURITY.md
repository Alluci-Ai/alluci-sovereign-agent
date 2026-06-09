# Security Policy

## Debug Mode
When the `DEBUG` environment flag is disabled, detailed error payloads are stripped from RPC responses and FastAPI global error messages to avoid leaking internal information. Enabling `DEBUG` (e.g., in development) will include full error details to aid troubleshooting.
