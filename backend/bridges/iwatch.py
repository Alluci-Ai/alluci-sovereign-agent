"""
Sovereign iWatch / HealthKit Bridge.

Pairing Protocol:
  1. User navigates to Settings > iWatch in the Alluci UI.
  2. Backend generates a TOTP seed (random bytes) and returns a QR code
     containing: {"url": "https://agent:8000", "seed": "<base32>", "device_id": "<uuid>"}
  3. Companion WatchOS app scans QR, stores seed.
  4. User taps "Confirm" on Watch → app computes TOTP(seed, current_time)
     and POSTs {"device_id": "<id>", "code": "<6-digit>"} to /api/channels/iwatch/pair
  5. Server verifies TOTP → issues a device session token (JWT, 90-day expiry).
  6. All subsequent biometric POSTs include:
     Authorization: Bearer <device_session_token>
     Content-Type: application/json
     Body: {"samples": [...TelemetryData...], "device_id": "..."}

HealthKit Metrics Sent by Watch:
  hr (int):               Heart rate in BPM
  hrv (int):              HRV SDNN in ms
  respiratory_rate (float): breaths/min
  stress_score (float):   0.0–100.0 (computed by Watch)
  energy_level (float):   0.0–1.0 (active energy / resting estimate)
  sleep_efficiency (float): 0.0–1.0 (from last sleep session)
  valence (float):        0.0–1.0 (optional, from mood logging)
  arousal (float):        0.0–1.0 (optional)
  focus (float):          0.0–1.0 (optional, from focus mode state)
  recorded_at (str):      ISO 8601 timestamp of sample
"""

import asyncio
import json
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .base import BridgeAdapter


class IWatchBridge(BridgeAdapter):
    """
    Production iWatch / HealthKit Bridge.
    Handles TOTP-based pairing, device session token issuance,
    batched telemetry ingestion, and ACE pipeline forwarding.
    """

    TOTP_STEP    = 30      # TOTP time step in seconds (RFC 6238)
    TOTP_DIGITS  = 6
    TOTP_WINDOW  = 1       # Accept ± 1 step (covers ~30s clock drift)
    SESSION_DAYS = 90      # Device session token validity

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self._paired_devices: Dict[str, Dict] = {}  # device_id → {seed, token, paired_at}
        self._pending_seeds:  Dict[str, str]  = {}  # device_id → base32 seed (pre-pair)
        self._telemetry_buffer: List[Dict]    = []
        self._buffer_maxsize: int = 500
        self._load_devices()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _devices_path(self) -> str:
        return os.path.join(self.vault_path, "paired_devices.json")

    def _load_devices(self) -> None:
        path = self._devices_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._paired_devices = json.load(f)
                self.logger.debug(
                    f"[IWATCH] Loaded {len(self._paired_devices)} paired devices."
                )
            except Exception as e:
                self.logger.error(f"[IWATCH] Failed to load devices: {e}")

    def _save_devices(self) -> None:
        path = self._devices_path()
        with open(path, "w") as f:
            json.dump(self._paired_devices, f)
        os.chmod(path, 0o600)

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any] = None) -> bool:
        """iWatch bridge is always available (no external service required)."""
        self.is_connected = True
        self.logger.info(
            f"[IWATCH] Bridge active. "
            f"Paired devices: {len(self._paired_devices)}"
        )
        return True

    # ── Pairing ───────────────────────────────────────────────────────────────

    async def generate_pairing_qr(self, agent_url: str) -> Dict[str, Any]:
        """
        Generate a new TOTP seed and QR payload for a Watch pairing session.
        Returns the QR data dict that should be JSON-encoded and displayed as QR.
        """
        device_id = secrets.token_hex(16)  # Unique device identifier
        seed      = secrets.token_bytes(20)
        seed_b32  = self._to_base32(seed)

        # Store pending seed (expires after 10 minutes)
        self._pending_seeds[device_id] = seed_b32
        asyncio.get_event_loop().call_later(600, self._pending_seeds.pop, device_id, None)

        qr_payload = {
            "url":       agent_url.rstrip("/"),
            "device_id": device_id,
            "seed":      seed_b32,
            "version":   1,
        }
        self.logger.info(f"[IWATCH] Pairing QR generated for device {device_id[:8]}…")
        return {"status": "ok", "qr_payload": qr_payload, "device_id": device_id}

    async def submit_pairing_code(self, code: str, device_id: str = "") -> Dict[str, Any]:
        """
        Verify the TOTP code from the Watch and issue a session token.
        Returns {"status": "SUCCESS", "session_token": "..."} on success.
        """
        if not device_id:
            return {"status": "FAILED", "error": "device_id required."}

        seed_b32 = self._pending_seeds.get(device_id)
        if not seed_b32:
            # Check if already paired (re-pairing flow)
            existing = self._paired_devices.get(device_id, {})
            seed_b32 = existing.get("seed")

        if not seed_b32:
            return {"status": "FAILED", "error": "No pending pairing for this device_id."}

        # Verify TOTP with ±window tolerance
        if not self._verify_totp(seed_b32, code):
            self.logger.warning(f"[IWATCH] TOTP verification failed for {device_id[:8]}…")
            return {"status": "FAILED", "error": "Invalid pairing code. Please retry."}

        # Issue device session token
        session_token = self._issue_session_token(device_id)

        # Record paired device
        self._paired_devices[device_id] = {
            "seed":      seed_b32,
            "token":     session_token,
            "paired_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=self.SESSION_DAYS)
            ).isoformat(),
        }
        self._pending_seeds.pop(device_id, None)
        self._save_devices()

        self.logger.info(f"[IWATCH] Device paired: {device_id[:8]}…")
        return {"status": "SUCCESS", "session_token": session_token, "device_id": device_id}

    def verify_device_token(self, token: str) -> Optional[str]:
        """
        Verify a device session token.
        Returns device_id if valid, None if expired or unknown.
        """
        for device_id, info in self._paired_devices.items():
            if info.get("token") == token:
                expires_at = info.get("expires_at")
                if expires_at:
                    exp = datetime.fromisoformat(expires_at)
                    if datetime.now(timezone.utc) > exp:
                        self.logger.warning(
                            f"[IWATCH] Session token expired for {device_id[:8]}…"
                        )
                        return None
                return device_id
        return None

    # ── TOTP Implementation ───────────────────────────────────────────────────

    @staticmethod
    def _to_base32(raw: bytes) -> str:
        import base64
        return base64.b32encode(raw).decode()

    def _compute_totp(self, seed_b32: str, ts: Optional[int] = None) -> str:
        """Compute RFC 6238 TOTP code."""
        try:
            import pyotp
            totp = pyotp.TOTP(seed_b32, digits=self.TOTP_DIGITS, interval=self.TOTP_STEP)
            return totp.at(ts or time.time())
        except ImportError:
            # Fallback pure-Python TOTP (requires only hmac + struct + hashlib)
            import base64
            import hashlib
            import hmac
            import struct

            key = base64.b32decode(seed_b32)
            t   = int((ts or time.time()) // self.TOTP_STEP)
            msg = struct.pack(">Q", t)
            h   = hmac.new(key, msg, hashlib.sha1).digest()
            offset = h[-1] & 0x0F
            code   = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
            return str(code % (10 ** self.TOTP_DIGITS)).zfill(self.TOTP_DIGITS)

    def _verify_totp(self, seed_b32: str, code: str) -> bool:
        """Verify TOTP code with ±TOTP_WINDOW tolerance."""
        now = time.time()
        for delta in range(-self.TOTP_WINDOW, self.TOTP_WINDOW + 1):
            ts = now + delta * self.TOTP_STEP
            if self._compute_totp(seed_b32, ts) == code:
                return True
        return False

    def _issue_session_token(self, device_id: str) -> str:
        """Issue a cryptographically random session token for a paired device."""
        return f"iwatch_{device_id[:8]}_{secrets.token_urlsafe(32)}"

    # ── Telemetry Ingestion ───────────────────────────────────────────────────

    async def ingest_telemetry(
        self, samples: List[Dict[str, Any]], device_id: str
    ) -> Dict[str, Any]:
        """
        Ingest a batch of HealthKit telemetry samples from the Watch.
        Each sample corresponds to TelemetryData fields.
        Samples are added to the buffer and forwarded to the ACE pipeline.
        """
        if not samples:
            return {"status": "ok", "processed": 0}

        processed = 0
        for sample in samples:
            # Normalise: add device metadata
            sample["device_id"]   = device_id
            sample["received_at"] = datetime.now(timezone.utc).isoformat()

            # Add to buffer for historical access
            self._telemetry_buffer.append(sample)
            if len(self._telemetry_buffer) > self._buffer_maxsize:
                self._telemetry_buffer.pop(0)

            # Forward to ACE via on_inbound callback
            if self.on_inbound:
                await self._dispatch_inbound({
                    "protocol":   "IWATCH",
                    "type":       "biometrics",
                    "device_id":  device_id,
                    "body":       f"[HealthKit sample: HR={sample.get('hr')} HRV={sample.get('hrv')}]",
                    "telemetry":  sample,
                    "timestamp":  sample.get("recorded_at", sample["received_at"]),
                })
            processed += 1

        self.last_activity = datetime.now(timezone.utc).isoformat()
        return {"status": "ok", "processed": processed}

    def get_recent_telemetry(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent telemetry samples from the buffer."""
        return self._telemetry_buffer[-limit:]

    # ── BridgeAdapter Interface ───────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        return {"status": "failed", "error": "iWatch is receive-only (HealthKit data in)."}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.get_recent_telemetry(limit)

    async def validate_integrity(self) -> bool:
        if not self.is_connected: return False
        import platform
        if platform.system() != "Darwin": return True
        # Optimized Darwin check: verify access to MobileSync to ensure perms exist
        sync_path = os.path.expanduser("~/Library/Application Support/MobileSync")
        return os.path.exists(sync_path)

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "paired_devices":  len(self._paired_devices),
            "pending_pairings": len(self._pending_seeds),
            "buffer_size":     len(self._telemetry_buffer),
            "pairing_ready":   True,
        })
        return h
