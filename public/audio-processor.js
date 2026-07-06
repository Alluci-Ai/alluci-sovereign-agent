class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.sampleRateOut = 16000;
    this.bufferSize = 3200; // 200ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize);
    this.bufferIndex = 0;
    this.lastInputIndex = 0;
    
    // Listen for sampleRate message from main thread
    this.port.onmessage = (event) => {
      if (event.data.type === 'init') {
        this.sampleRateIn = event.data.sampleRate || 48000;
        this.ratio = this.sampleRateIn / this.sampleRateOut;
      }
    };
    
    this.ratio = 3; // Default 48k -> 16k
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0 || !input[0]) return true;

    const channelData = input[0];

    // Downsample & convert to 16-bit PCM
    for (let i = 0; i < channelData.length; i++) {
      this.lastInputIndex += 1;
      if (this.lastInputIndex >= this.ratio) {
        this.lastInputIndex -= this.ratio;
        
        // Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
        let sample = Math.max(-1, Math.min(1, channelData[i]));
        this.buffer[this.bufferIndex++] = sample < 0 ? sample * 32768 : sample * 32767;

        if (this.bufferIndex >= this.bufferSize) {
          // Send the 200ms buffer to the main thread
          // We make a copy of the buffer to transfer to prevent detached array issues
          const outBuffer = new Int16Array(this.buffer);
          this.port.postMessage({ type: 'audio', data: outBuffer.buffer }, [outBuffer.buffer]);
          this.bufferIndex = 0;
        }
      }
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
