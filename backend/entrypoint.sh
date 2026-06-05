#!/bin/bash
set -e

# Load Docker secrets from /run/secrets/ into environment variables
if [ -d "/run/secrets/" ]; then
    for secret in /run/secrets/*; do
        if [ -f "$secret" ]; then
            secret_name=$(basename "$secret")
            # Convert to uppercase
            secret_env=$(echo "$secret_name" | tr '[:lower:]' '[:upper:]')
            export "$secret_env"="$(cat "$secret")"
        fi
    done
fi

# Execute the main command
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
