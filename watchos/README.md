# AlluciWatch — watchOS HealthKit Integration

The AlluciWatch application is a native Swift/WatchKit implementation that bridges biometric data from HealthKit to the Alluci Sovereign Agent.

## Implementation Status
- **Models**: `TelemetrySample.swift` (Matches backend `TelemetryData`)
- **Managers**: 
  - `HealthKitManager.swift` (Live HR/HRV monitoring)
  - `NetworkManager.swift` (TOTP Pairing & Telemetry Ingestion)
- **UI**: SwiftUI-based pairing and monitoring views.

## Setup Instructions
1. Open the project in Xcode (requires Mac).
2. Ensure the `HealthKit` capability is enabled.
3. Deploy to your Apple Watch.
4. Open **Settings > iWatch** on your Alluci Desktop Agent to get your Pairing QR.
5. Enter the **Agent URL**, **Device ID**, and **TOTP Code** into the watch app.
6. Tap **Connect** to start the physiological feedback loop.

## Automatic Monitoring
Once paired, tapping **Start Tracking** will:
1. Initialize an `HKObserverQuery` for heart rate changes.
2. Batched samples are sent via POST to `/api/bridge/iwatch/biometrics`.
3. The ACE engine on the backend processes this data to adjust the agent's autonomy and flow mode.

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
