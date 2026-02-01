import { useState, useEffect, useRef, useCallback } from 'react';

export const useAudio = () => {
  const [isListening, setIsListening] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const outputDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const audioOutputRef = useRef<HTMLAudioElement | null>(null);

  const startListening = useCallback(async (onAudioData: (data: ArrayBuffer) => void, deviceId?: string) => {
    try {
      const constraints = { 
        audio: { 
            deviceId: deviceId ? { exact: deviceId } : undefined,
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
        } 
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 16000,
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;
      
      // Buffer size 4096 gives ~256ms latency at 16k
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const inputSampleRate = audioContext.sampleRate;
        const targetSampleRate = 16000;
        
        let finalData = inputData;

        // Downsample if needed
        if (inputSampleRate > targetSampleRate) {
            const ratio = inputSampleRate / targetSampleRate;
            const newLength = Math.floor(inputData.length / ratio);
            finalData = new Float32Array(newLength);
            for (let i = 0; i < newLength; i++) {
                finalData[i] = inputData[Math.floor(i * ratio)];
            }
        }
        
        // Calculate volume for visualization (using downsampled data is fine)
        let sum = 0;
        for (let i = 0; i < finalData.length; i++) {
             sum += finalData[i] * finalData[i];
        }
        const rms = Math.sqrt(sum / finalData.length);
        setAudioLevel(Math.min(rms * 5, 1)); 

        // Convert Float32 to Int16 PCM
        const pcmData = new Int16Array(finalData.length);
        for (let i = 0; i < finalData.length; i++) {
             let s = Math.max(-1, Math.min(1, finalData[i]));
             pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        onAudioData(pcmData.buffer);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsListening(true);
      nextStartTimeRef.current = audioContext.currentTime;

    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current = null;
    }
    if (sourceRef.current) {
        sourceRef.current.disconnect();
        sourceRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioOutputRef.current) {
        audioOutputRef.current.pause();
        audioOutputRef.current.srcObject = null;
        audioOutputRef.current = null;
    }
    if (outputDestRef.current) {
        outputDestRef.current.disconnect();
        outputDestRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsListening(false);
    setAudioLevel(0);
  }, []);

  const playAudioChunk = useCallback((base64Data: string) => {
      // Ensure we have an audio context for playback even if not listening
      if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
          nextStartTimeRef.current = audioContextRef.current.currentTime;
      }
      
      const ctx = audioContextRef.current;

      // Initialize HTMLAudioElement output for AEC support
      if (!outputDestRef.current) {
          outputDestRef.current = ctx.createMediaStreamDestination();
          audioOutputRef.current = new Audio();
          audioOutputRef.current.srcObject = outputDestRef.current.stream;
          audioOutputRef.current.play().catch(e => console.error("Audio playback error:", e));
      }

      try {
        const binaryString = window.atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const int16Data = new Int16Array(bytes.buffer);
        const float32Data = new Float32Array(int16Data.length);
        for (let i = 0; i < int16Data.length; i++) {
            float32Data[i] = int16Data[i] / 32768.0;
        }

        // Gemini Live Audio is typically 24kHz
        const buffer = ctx.createBuffer(1, float32Data.length, 24000); 
        buffer.copyToChannel(float32Data, 0);

        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(outputDestRef.current);
        
        const currentTime = ctx.currentTime;
        // Basic scheduling to prevent gaps
        const startTime = Math.max(currentTime, nextStartTimeRef.current);
        source.start(startTime);
        nextStartTimeRef.current = startTime + buffer.duration;
      } catch (e) {
          console.error("Error playing audio chunk", e);
      }
  }, []);

  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  return { isListening, audioLevel, startListening, stopListening, playAudioChunk };
};