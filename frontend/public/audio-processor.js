class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bytesWritten = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];

    if (input.length > 0) {
      const inputChannel = input[0];
      
      // Append to buffer
      for (let i = 0; i < inputChannel.length; i++) {
        this.buffer[this.bytesWritten++] = inputChannel[i];
        
        // When buffer is full, process and flush
        if (this.bytesWritten >= this.bufferSize) {
            this.flush();
        }
      }
    }

    return true; // Keep processor alive
  }

  flush() {
    // Send full buffer to main thread
    // We send the raw Float32 data; main thread handles downsampling/encoding
    // to avoid duplicating complex logic in the worklet for now.
    // Or we can do it here for performance? 
    // Let's pass the raw float32 buffer to keep it simple and ensure message passing is fast.
    
    // We must slice because the buffer is reused
    const dataToSend = this.buffer.slice(0, this.bufferSize);
    this.port.postMessage(dataToSend);
    this.bytesWritten = 0;
  }
}

registerProcessor('audio-processor', AudioProcessor);
