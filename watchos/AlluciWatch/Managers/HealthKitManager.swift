import Foundation
import HealthKit

class HealthKitManager: ObservableObject {
    let healthStore = HKHealthStore()
    
    @Published var lastHeartRate: Double = 0
    @Published var lastHRV: Double = 0
    @Published var isAuthorized: Bool = false
    
    private var anchor: HKQueryAnchor?
    private var hrvQuery: HKAnchoredObjectQuery?
    private var runtimeSession: WKExtendedRuntimeSession?
    
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
    
    func startBackgroundCollection() {
        // 1. Start Heart Rate Observer Query
        startHeartRateQuery { _ in }
        
        // 2. Start HRV Anchored Object Query
        startHRVQuery()
        
        // 3. Keep app alive in background
        runtimeSession = WKExtendedRuntimeSession()
        runtimeSession?.start()
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
    
    private func startHRVQuery() {
        let hrvType = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!
        
        let query = HKAnchoredObjectQuery(type: hrvType, predicate: nil, anchor: anchor, limit: HKObjectQueryNoLimit) { (query, samples, deletedObjects, newAnchor, error) in
            self.anchor = newAnchor
            self.processHRVSamples(samples)
        }
        
        query.updateHandler = { (query, samples, deletedObjects, newAnchor, error) in
            self.anchor = newAnchor
            self.processHRVSamples(samples)
        }
        
        self.hrvQuery = query
        healthStore.execute(query)
    }
    
    private func processHRVSamples(_ samples: [HKSample]?) {
        guard let samples = samples as? [HKQuantitySample], let lastSample = samples.last else { return }
        let hrvUnit = HKUnit.secondUnit(with: .milli)
        let hrvValue = lastSample.quantity.doubleValue(for: hrvUnit)
        
        DispatchQueue.main.async {
            self.lastHRV = hrvValue
        }
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
        let hr = Int(lastHeartRate)
        let hrv = Int(lastHRV)
        
        return TelemetrySample(
            hr: hr > 0 ? hr : nil,
            hrv: hrv > 0 ? hrv : nil,
            timestamp: ISO8601DateFormatter().string(from: Date())
        )
    }
}
