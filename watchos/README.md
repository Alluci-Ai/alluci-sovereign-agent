# Alluci WatchOS Companion Bridge

This directory contains the documentation and core bridge logic for the Alluci Apple Watch companion.

## Overview
The Alluci WatchOS app serves as a physiological sensor node that streams Heart Rate (HR) and Heart Rate Variability (HRV) data to the Sovereign Agent to inform the **ACE (Affective Control Engine)**.

## Core Bridge Logic (Swift)

Below is the standard snippet for POSTing telemetry to the agent.

```swift
import Foundation
import HealthKit

class AlluciTelemetrySender {
    let agentURL = URL(string: "http://your-agent-ip:8000/api/telemetry")!
    var authToken: String? // JWT obtained from login

    func sendVitals(hr: Double, hrv: Double, stress: Double) {
        var request = URLRequest(url: agentURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let payload: [String: Any] = [
            "hr": hr,
            "hrv": hrv,
            "stress_score": stress,
            "focus": 0.5 // Default/computed
        ]

        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)

        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Telemetry error: \(error)")
                return
            }
            print("Telemetry sent successfully.")
        }
        task.resume()
    }
}
```

## Integration with ACE
- **RECOVERY_MODE**: Triggered when `stress_score > 75`.
- **PEAK_PERFORMANCE**: Triggered when `vitality > 0.8` (computed from low stress and high HRV stability).
- **DEEP_WORK**: Triggered when reported `focus > 0.8`.

## Setup Instructions
1. Ensure your iPhone and Mac/Raspberry Pi are on the same local network.
2. The WatchOS app requires **HealthKit** permissions for Heart Rate.
3. Use the `scripts/telemetry_sim.py` tool on the Mac to test the integration before deploying the native app.
