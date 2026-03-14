import Foundation
import HealthKit

class HealthKitManager: ObservableObject {
    let healthStore = HKHealthStore()
    
    @Published var lastHeartRate: Double = 0
    @Published var lastHRV: Double = 0
    @Published var isAuthorized: Bool = false
    
    private var anchor: HKQueryAnchor?
    
    let typesToRead: Set = [
        HKObjectType.quantityType(forIdentifier: .heartRate)!,
        HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!,
        HKObjectType.quantityType(forIdentifier: .respiratoryRate)!,
        HKObjectType.quantityType(forIdentifier: .restingHeartRate)!,
        HKObjectType.categoryType(forIdentifier: .sleepAnalysis)!
    ]
    
    func requestAuthorization() {
        healthStore.requestAuthorization(toShare: nil, read: typesToRead) { success, error in
            DispatchQueue.main.async {
                self.isAuthorized = success
            }
        }
    }
    
    func startHeartRateQuery(onUpdate: @escaping (Int) -> Void) {
        let sampleType = HKObjectType.quantityType(forIdentifier: .heartRate)!
        let query = HKObserverQuery(sampleType: sampleType, predicate: nil) { query, completionHandler, error in
            if error != nil { return }
            
            self.fetchLatestSamples(for: sampleType) { samples in
                if let lastSample = samples.last as? HKQuantitySample {
                    let hrUnit = HKUnit.count().unitDivided(by: HKUnit.minute())
                    let hr = Int(lastSample.quantity.doubleValue(for: hrUnit))
                    DispatchQueue.main.async {
                        self.lastHeartRate = Double(hr)
                    }
                    onUpdate(hr)
                }
                completionHandler()
            }
        }
        healthStore.execute(query)
    }
    
    func fetchLatestSamples(for sampleType: HKSampleType, completion: @escaping ([HKSample]) -> Void) {
        let predicate = HKQuery.predicateForSamples(withStart: Date().addingTimeInterval(-3600), end: Date(), options: .strictEndDate)
        let sortDescriptor = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)
        
        let query = HKSampleQuery(sampleType: sampleType, predicate: predicate, limit: 1, sortDescriptors: [sortDescriptor]) { query, results, error in
            completion(results ?? [])
        }
        healthStore.execute(query)
    }
    
    func getCurrentTelemetry() async -> TelemetrySample {
        // In a real app, this would perform multiple async fetches for all types
        // Here we provide a simplified sample gathering
        let hr = Int(lastHeartRate)
        let hrv = Int(lastHRV)
        
        return TelemetrySample(
            hr: hr > 0 ? hr : nil,
            hrv: hrv > 0 ? hrv : nil
        )
    }
}
