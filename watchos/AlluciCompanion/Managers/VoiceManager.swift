import Foundation
import Speech
import AVFoundation

class VoiceManager: ObservableObject {
    // MARK: - Native Apple Fallback (Scenario B/C)
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    
    // MARK: - Sovereign Pipeline (Scenario A)
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    
    @Published var isRecording = false
    @Published var transcribedText = ""
    @Published var isAuthorized = false
    
    init() {
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: nil)
    }
    
    func requestAuthorization() {
        SFSpeechRecognizer.requestAuthorization { authStatus in
            DispatchQueue.main.async {
                self.isAuthorized = authStatus == .authorized
            }
        }
        AVAudioSession.sharedInstance().requestRecordPermission { _ in }
    }
    
    func toggleRecording(route: RoutingState = .tethered) {
        if isRecording {
            stopRecording(route: route)
        } else {
            do {
                if route == .tethered {
                    try startStreamingPCM()
                } else {
                    try startNativeRecording()
                }
            } catch {
                print("Failed to start recording: \(error)")
            }
        }
    }
    
    // MARK: - Sovereign 16kHz PCM Capture (For Whisper)
    private func startStreamingPCM() throws {
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: .duckOthers)
        try audioSession.setActive(true)
        
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        // Target format for Whisper: 16kHz, 1 channel, Int16 PCM
        guard let whisperFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true) else { return }
        guard let converter = AVAudioConverter(from: recordingFormat, to: whisperFormat) else { return }
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            let capacity = AVAudioFrameCount(whisperFormat.sampleRate * Double(buffer.frameLength) / recordingFormat.sampleRate)
            guard let convertedBuffer = AVAudioPCMBuffer(pcmFormat: whisperFormat, frameCapacity: capacity) else { return }
            
            var error: NSError?
            var allSamplesReceived = false
            converter.convert(to: convertedBuffer, error: &error) { inNumPackets, outStatus in
                if allSamplesReceived {
                    outStatus.pointee = .noDataNow
                    return nil
                }
                allSamplesReceived = true
                outStatus.pointee = .haveData
                return buffer
            }
            
            // Here we would stream `convertedBuffer` byte array to TCPSocketServer
            // TCPSocketServer.shared.send(pcmData)
        }
        
        audioEngine.prepare()
        try audioEngine.start()
        
        DispatchQueue.main.async {
            self.isRecording = true
            self.transcribedText = "[Streaming Raw PCM to Desktop...]"
        }
    }
    
    // MARK: - Native Apple SFSpeechRecognizer Fallback
    private func startNativeRecording() throws {
        recognitionTask?.cancel()
        self.recognitionTask = nil
        
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
        try audioSession.setActive(true)
        
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let recognitionRequest = recognitionRequest else { fatalError("Unable to create request") }
        recognitionRequest.shouldReportPartialResults = true
        
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            self.recognitionRequest?.append(buffer)
        }
        
        audioEngine.prepare()
        try audioEngine.start()
        
        recognitionTask = speechRecognizer?.recognitionTask(with: recognitionRequest) { result, error in
            var isFinal = false
            if let result = result {
                DispatchQueue.main.async {
                    self.transcribedText = result.bestTranscription.formattedString
                }
                isFinal = result.isFinal
            }
            if error != nil || isFinal {
                self.stopRecording(route: .offlineFallback)
            }
        }
        
        DispatchQueue.main.async {
            self.isRecording = true
            self.transcribedText = ""
        }
    }
    
    private func stopRecording(route: RoutingState) {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        if route != .tethered {
            recognitionRequest?.endAudio()
        }
        DispatchQueue.main.async {
            self.isRecording = false
        }
    }
    
    // MARK: - Sovereign 48kHz PCM Playback (Kokoro)
    func playIncomingPCM(_ pcmData: Data) {
        // Format of Kokoro output: 48kHz, Int16 or Float32, 1 channel
        guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 48000, channels: 1, interleaved: false) else { return }
        
        // Convert Data to AVAudioPCMBuffer and schedule
        // Mocking the ingestion since actual byte conversion requires UnsafePointer arithmetic
        let frameCount = AVAudioFrameCount(pcmData.count / 4)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount) else { return }
        buffer.frameLength = frameCount
        
        try? audioEngine.start()
        playerNode.scheduleBuffer(buffer, completionHandler: nil)
        playerNode.play()
    }
    
    // MARK: - Native Text-to-Speech Fallback
    private let synthesizer = AVSpeechSynthesizer()
    
    func speak(text: String, route: RoutingState = .tethered) {
        if route == .tethered {
            // Handled by playIncomingPCM streaming from desktop
            return
        }
        
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = 0.5
        
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: .duckOthers)
        try? AVAudioSession.sharedInstance().setActive(true)
        
        synthesizer.speak(utterance)
    }
}
