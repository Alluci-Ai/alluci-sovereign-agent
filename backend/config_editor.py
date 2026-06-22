"""
Schema-Driven Configuration Editor for the Polytope Sovereign OS.

Serves the current configuration as a JSON Schema, accepts validated
updates via API, and hot-applies changes without restart.

Reference: Sovereign Spec Sections 8.1–8.3
"""

import json
import logging
from .logging_config import get_logger
import os
from typing import Dict, Any

logger = get_logger("ConfigEditor")


class ConfigEditor:
    """
    Provides a runtime configuration editor that:
    1. Exposes the current config as JSON + JSON Schema
    2. Validates incoming changes against the schema
    3. Hot-applies changes to the in-memory settings object
    4. Persists changes to .env for cold-boot consistency
    """

    # Fields that may NEVER be changed at runtime (security-critical)
    IMMUTABLE_FIELDS = frozenset({
        "POLYTOPE_MASTER_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL",
    })

    # Fields that are safe to hot-apply without restart
    HOT_APPLY_FIELDS = frozenset({
        "APP_ENV",
        "ALLOWED_ORIGINS",
        "MAX_AUTONOMY_RETRIES",
        "CRITIC_THRESHOLD",
        "MAX_CONCURRENT_TASKS",
        "RATE_LIMIT_PER_MINUTE",
        "LOCAL_LCE_URL",
        "PIPER_PATH",
        "PIPER_MODEL",
        "WHISPER_CPP_PATH",
        "HOST",
        "PORT",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "NVIDIA_NIM_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
        "OPENROUTER_API_KEY",
        "VERUS_RPC_HOST",
        "VERUS_RPC_PORT",
        "VERUS_RPC_USER",
        "VERUS_RPC_PASSWORD",
        "VERUS_INTEGRATION_MODE",
        "VERUS_ID_IDENTITY",
        "VERUS_ID_PRIVATE_KEY",
        "AUTH_COOKIE_NAME",
        "AUTH_COOKIE_SAMESITE",
        "REDIS_URL",
    })

    def __init__(self, settings_instance):
        self._settings = settings_instance

    # ── Read ──────────────────────────────────────────────────────────────

    def get_config(self) -> Dict[str, Any]:
        """Return current config values (sensitive fields masked)."""
        data = {}
        for field_name, field_info in self._settings.model_fields.items():
            value = getattr(self._settings, field_name, None)
            # Mask sensitive values
            if self._is_sensitive(field_name) and value:
                data[field_name] = self._mask(str(value))
            else:
                data[field_name] = value  # type: ignore
        return data

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the JSON Schema derived from the Pydantic Settings model.
        Annotates each field with mutability info.
        """
        schema = self._settings.model_json_schema()

        # Annotate properties with mutability
        props = schema.get("properties", {})
        for field_name in props:
            if field_name in self.IMMUTABLE_FIELDS:
                props[field_name]["x-immutable"] = True
            elif field_name in self.HOT_APPLY_FIELDS:
                props[field_name]["x-hot-apply"] = True
            if self._is_sensitive(field_name):
                props[field_name]["x-sensitive"] = True

        return schema

    # ── Write ─────────────────────────────────────────────────────────────

    def apply_overrides(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and hot-apply configuration overrides.

        Returns: {"applied": [...], "rejected": [...], "restart_required": bool}
        """
        applied = []
        rejected = []
        restart_needed = False

        for key, value in overrides.items():
            # 1. Block immutable fields
            if key in self.IMMUTABLE_FIELDS:
                rejected.append({
                    "field": key,
                    "reason": "Immutable — cannot be changed at runtime",
                })
                continue

            # 2. Check field exists on settings
            if not hasattr(self._settings, key):
                rejected.append({
                    "field": key,
                    "reason": "Unknown configuration field",
                })
                continue

            # 3. Apply to in-memory settings
            try:
                old_value = getattr(self._settings, key)
                setattr(self._settings, key, value)
                applied.append({"field": key, "old": self._safe_str(old_value), "new": self._safe_str(value)})

                # 4. Persist to environment (for subprocess visibility)
                if isinstance(value, (list, dict)):
                    os.environ[key] = json.dumps(value)
                else:
                    os.environ[key] = str(value)

                # 5. Check if restart is needed
                if key not in self.HOT_APPLY_FIELDS:
                    restart_needed = True

            except Exception as e:
                rejected.append({
                    "field": key,
                    "reason": f"Validation error: {e}",
                })

        # 6. Persist to .env file for cold-boot consistency
        if applied:
            self._persist_to_env(overrides)

        return {
            "applied": applied,
            "rejected": rejected,
            "restart_required": restart_needed,
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def _persist_to_env(self, overrides: Dict[str, Any]):
        """
        Write changed values to .env file.
        Only updates keys that were successfully applied.
        """
        env_path = ".env"
        if not os.path.exists(env_path):
            return

        try:
            with open(env_path, "r") as f:
                lines = f.readlines()

            updated_keys = set()
            new_lines = []

            for line in lines:
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#"):
                    key = stripped.split("=", 1)[0].strip()
                    if key in overrides:
                        value = overrides[key]
                        if isinstance(value, (list, dict)):
                            new_lines.append(f'{key}={json.dumps(value)}\n')
                        else:
                            new_lines.append(f"{key}={value}\n")
                        updated_keys.add(key)
                        continue
                new_lines.append(line)

            # Append any new keys not already in .env
            for key, value in overrides.items():
                if key not in updated_keys and key not in self.IMMUTABLE_FIELDS:
                    if isinstance(value, (list, dict)):
                        new_lines.append(f'{key}={json.dumps(value)}\n')
                    else:
                        new_lines.append(f"{key}={value}\n")

            with open(env_path, "w") as f:
                f.writelines(new_lines)

            logger.info(f"[ConfigEditor] Persisted {len(overrides)} changes to .env")

        except Exception as e:
            logger.error(f"[ConfigEditor] Failed to persist to .env: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _is_sensitive(field_name: str) -> bool:
        sensitive_keywords = {"KEY", "SECRET", "PASSWORD", "TOKEN", "PRIVATE"}
        return any(kw in field_name.upper() for kw in sensitive_keywords)

    @staticmethod
    def _mask(value: str, visible: int = 4) -> str:
        if len(value) <= visible:
            return "****"
        return value[:visible] + "****" + value[-2:]

    @staticmethod
    def _safe_str(value) -> str:
        if isinstance(value, str) and len(value) > 20:
            return value[:8] + "..."
        return str(value)
