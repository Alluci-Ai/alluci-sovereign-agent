# Swift Companion App Protocol Reference

This document defines the HTTP protocol the WatchOS Swift companion app must implement to communicate with the Sovereign iWatch bridge.

## 1. Pairing Flow

The pairing process establishes a trusted link between the Apple Watch and the Sovereign Agent.

### Step 1: Request Pairing QR
The Watch app (or a setup UI in the mobile companion) requests the pairing seed.

**GET** `/api/channels/iwatch/pairing-qr`  
**Headers:** `Authorization: Bearer <user_jwt>`

**Response:**
```json
{
  "status": "ok",
  "device_id": "a1b2c3d4...",
  "qr_payload": {
    "url":       "https://agent.yourdomain.com",
    "device_id": "a1b2c3d4...",
    "seed":      "BASE32ENCODEDTOTP...",
    "version":   1
  }
}
```

*Note: The Watch app encodes the `qr_payload` as a JSON string within a QR code for the user to scan if setting up via the Watch directly, or receives it via the iOS companion app.*

### Step 2: Confirm Pairing
On the Watch, after scanning the QR and tapping "Confirm", the app computes the current TOTP code and submits it.

**POST** `/api/channels/iwatch/pair`  
**Body:**
```json
{
  "device_id": "a1b2c3d4...",
  "code": "123456"
}
```

**Response:**
```json
{
  "status": "SUCCESS",
  "session_token": "iwatch_a1b2c3d4_<random>",
  "device_id": "a1b2c3d4..."
}
```

**Action:** The Watch app MUST store the `session_token` securely in the **Watch Keychain**.

---

## 2. Telemetry Submission

The Watch app should periodically submit physiological and environmental samples to the agent.

**POST** `/api/bridge/iwatch/biometrics`  
**Headers:**  
- `Authorization: Bearer <session_token>`  
- `Content-Type: application/json`

**Body:**
```json
{
  "device_id": "a1b2c3d4...",
  "samples": [
    {
      "hr":               72,
      "hrv":              45,
      "respiratory_rate": 16.2,
      "stress_score":     23.5,
      "energy_level":     0.78,
      "sleep_efficiency": 0.85,
      "valence":          0.6,
      "arousal":          0.4,
      "focus":            0.7,
      "recorded_at":      "2026-03-13T10:30:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "status": "SUCCESS",
  "processed": 1,
  "flow_intervention": {
    "mode": "STANDARD", 
    "action": "NORMAL_ROUTING"
  },
  "resonance": 0.77
}
```

---

## 3. Recommended Submission Cadence

To balance battery life and real-time responsiveness, the following cadence is recommended:

| Condition | Interval | Batch Size |
| :--- | :--- | :--- |
| **Idle / Background** | 60s | 1 sample |
| **Active Workout** | 10s | 1 sample |
| **Offline / BLE Gap** | On Reconnect | Up to 50 buffered samples |
| **Low Battery (<20%)** | 120s | 1 sample |

---

## 4. Retrieving History

To sync state or display historical trends on the Watch UI.

**GET** `/api/bridge/iwatch/telemetry`  
**Headers:** `Authorization: Bearer <user_jwt_or_session_token>`  
**Query Params:** `limit` (default 20, max 200)

**Response:**
```json
{
  "samples": [...],
  "count": 20
}
```
