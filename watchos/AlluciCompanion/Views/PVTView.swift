import SwiftUI

struct PVTView: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var backgroundColor: Color = .black
    @State private var text: String = "Tap anywhere to start"
    @State private var isWaiting = false
    @State private var isStimulusActive = false
    @State private var startTime: Date?
    @State private var reactionTimes: [Double] = []
    @State private var currentTrial = 0
    let totalTrials = 5
    
    var body: some View {
        ZStack {
            backgroundColor.edgesIgnoringSafeArea(.all)
            
            VStack {
                Text("PVT Test (\(currentTrial)/\(totalTrials))")
                    .font(.caption)
                    .foregroundColor(.white)
                    .padding(.top, 40)
                Spacer()
                Text(text)
                    .font(.title)
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                    .padding()
                Spacer()
            }
        }
        .onTapGesture {
            handleTap()
        }
        .navigationBarHidden(true)
    }
    
    private func handleTap() {
        if !isWaiting && !isStimulusActive && currentTrial == 0 {
            // Start the test
            startTrial()
        } else if isWaiting && !isStimulusActive {
            // False Start
            text = "False Start! Wait for Green."
            resetTrial()
        } else if isStimulusActive {
            // Valid Tap
            guard let start = startTime else { return }
            let reactionTime = Date().timeIntervalSince(start) * 1000 // in ms
            reactionTimes.append(reactionTime)
            
            currentTrial += 1
            if currentTrial >= totalTrials {
                finishTest()
            } else {
                text = String(format: "Reaction: %.0f ms", reactionTime)
                resetTrial()
            }
        }
    }
    
    private func resetTrial() {
        isStimulusActive = false
        backgroundColor = .black
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if currentTrial < totalTrials {
                self.startTrial()
            }
        }
    }
    
    private func startTrial() {
        isWaiting = true
        text = "Wait for Green..."
        backgroundColor = .red
        
        let randomDelay = Double.random(in: 2.0...5.0)
        DispatchQueue.main.asyncAfter(deadline: .now() + randomDelay) {
            if self.isWaiting {
                self.isWaiting = false
                self.isStimulusActive = true
                self.backgroundColor = .green
                self.text = "TAP NOW!"
                self.startTime = Date()
            }
        }
    }
    
    private func finishTest() {
        isStimulusActive = false
        isWaiting = false
        let avg = reactionTimes.reduce(0, +) / Double(reactionTimes.count)
        text = String(format: "Test Complete.\nAvg: %.0f ms", avg)
        backgroundColor = .blue
        
        // Auto dismiss after 2s
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            // Here you'd normally post this to ACE Engine state via a delegate or environment object
            NotificationCenter.default.post(name: NSNotification.Name("PVTCompleted"), object: avg)
            self.presentationMode.wrappedValue.dismiss()
        }
    }
}
