// [ PPN-030 ] Sovereign Voice Activity Detection (VAD) Edge Worklet
// Executes strictly on the device audio thread. No 3rd-party dependencies.

class VADProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.SAMPLING_RATE = 16000;
        this.TARGET_WINDOW_SIZE = Math.floor(this.SAMPLING_RATE * 0.200);
        
        this.DEFAULT_ENERGY_THRESHOLD = 0.035;
        this.dynamicEnergyThreshold = 0.035;
        this.calibrationChunks = 0;
        this.totalCalibrationRms = 0;
        this.isCalibrated = false;

        this.rollingCache = new Float32Array(this.TARGET_WINDOW_SIZE);
        this.cacheIndex = 0;
    }

    process(inputs, outputs, parameters) {
        // We only care about the first input and its first channel (mono)
        const inputChannel = inputs[0]?.[0];
        if (!inputChannel) return true; // Keep processor alive

        for (let i = 0; i < inputChannel.length; i++) {
            this.rollingCache[this.cacheIndex++] = inputChannel[i];

            if (this.cacheIndex >= this.TARGET_WINDOW_SIZE) {
                this.evaluateAndEmitChunk();
                this.cacheIndex = 0;
            }
        }

        return true; // Keep processor alive
    }

    evaluateAndEmitChunk() {
        let totalRmsEnergy = 0.0;
        for (let i = 0; i < this.TARGET_WINDOW_SIZE; i++) {
            totalRmsEnergy += this.rollingCache[i] * this.rollingCache[i];
        }
        totalRmsEnergy = Math.sqrt(totalRmsEnergy / this.TARGET_WINDOW_SIZE);

        // Hardcode a robust, fixed threshold to eliminate startup latency and prevent calibration on active speech
        const currentThreshold = 0.015;
        const containsActiveSpeech = totalRmsEnergy > currentThreshold;

        // Post back to main thread (bridgeManager.ts)
        const chunk = new Float32Array(this.rollingCache);
        this.port.postMessage({
            pcmFrameBuffer: chunk,
            containsActiveSpeech,
            accumulatedSampleCount: this.TARGET_WINDOW_SIZE
        }, [chunk.buffer]);
    }
}

registerProcessor('vad-processor', VADProcessor);
