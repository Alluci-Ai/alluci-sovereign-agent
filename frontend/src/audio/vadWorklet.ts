// [ PPN-030 ] Sovereign Voice Activity Detection (VAD) Edge Worklet
// Executes strictly on the device audio thread. No 3rd-party dependencies.

declare abstract class AudioWorkletProcessor {
    readonly port: MessagePort;
    constructor();
    abstract process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare function registerProcessor(name: string, processorCtor: (new (options?: any) => AudioWorkletProcessor)): void;

// eslint-disable-next-line @typescript-eslint/no-unused-vars
interface AudioChunkManifest {
    pcmFrameBuffer: Float32Array;
    containsActiveSpeech: boolean;
    accumulatedSampleCount: number;
}

class VADProcessor extends AudioWorkletProcessor {
    private readonly SAMPLING_RATE = 16000;
    private readonly TARGET_WINDOW_SIZE: number;
    private readonly DEFAULT_ENERGY_THRESHOLD = 0.035;

    private dynamicEnergyThreshold: number = 0.035;
    private calibrationChunks: number = 0;
    private totalCalibrationRms: number = 0;
    private isCalibrated: boolean = false;

    private rollingCache: Float32Array;
    private cacheIndex: number = 0;

    constructor() {
        super();
        // 200ms audio window
        this.TARGET_WINDOW_SIZE = Math.floor(this.SAMPLING_RATE * 0.200);
        this.rollingCache = new Float32Array(this.TARGET_WINDOW_SIZE);
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean {
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

    private evaluateAndEmitChunk() {
        let totalRmsEnergy = 0.0;
        for (let i = 0; i < this.TARGET_WINDOW_SIZE; i++) {
            totalRmsEnergy += this.rollingCache[i] * this.rollingCache[i];
        }
        totalRmsEnergy = Math.sqrt(totalRmsEnergy / this.TARGET_WINDOW_SIZE);

        if (!this.isCalibrated) {
            this.calibrationChunks++;
            this.totalCalibrationRms += totalRmsEnergy;
            if (this.calibrationChunks >= 5) {
                const avgAmbient = this.totalCalibrationRms / this.calibrationChunks;
                // Calibrate threshold at 2.5x average ambient noise, bounded between 0.015 and 0.08
                this.dynamicEnergyThreshold = Math.max(0.015, Math.min(0.08, avgAmbient * 2.5));
                this.isCalibrated = true;
                // eslint-disable-next-line no-console
                console.log(`[VAD Worklet] Calibrated. Dynamic energy threshold: ${this.dynamicEnergyThreshold.toFixed(4)}`);
            }
        }

        const currentThreshold = this.isCalibrated ? this.dynamicEnergyThreshold : this.DEFAULT_ENERGY_THRESHOLD;
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
