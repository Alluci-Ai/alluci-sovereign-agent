# ---- Builder stage ---------------------------------------------------------
FROM python:3.11-slim AS builder

# Install build‑time tools needed for compiling any wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git && rm -rf /var/lib/apt/lists/*

# Create a non‑root user (will also be used in the runtime stage)
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# Copy only the lockfile first to leverage Docker cache
COPY requirements.txt .

# Install **all** dependencies (including dev) – this layer is discarded later
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# ---- Runtime stage --------------------------------------------------------
FROM python:3.11-slim AS runtime

# Create the same non‑root user in the final image
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# Copy only the compiled packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app
# Copy TLS assets (read‑only for the non‑root user)
COPY --chown=appuser:appuser certs /app/certs

# Ensure the app files are owned by the non‑root user
RUN chown -R appuser:appuser /app

# Switch to non‑root user
USER appuser

# Expose the FastAPI port and TLS port
EXPOSE 8000 8443

# Entrypoint – start the FastAPI server with uvicorn (TLS)
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8443", "--ssl-keyfile", "/app/certs/server.key", "--ssl-certfile", "/app/certs/server.crt"]
