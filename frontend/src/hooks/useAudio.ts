import { useState, useEffect, useRef, useCallback } from 'react';

export const useAudio = () => {
  const [isListening, setIsListening] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [pcmRms, setPcmRms] = useState(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<AudioNode | null>(null);
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
      
      const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
          sampleRate: 16000,
      });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;
      
      const processor = audioContext.createScriptProcessor(2048, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const inputSampleRate = audioContext.sampleRate;
        const targetSampleRate = 16000;
        
        let finalData = inputData;

        // Downsample (Box Filter)
        if (inputSampleRate > targetSampleRate) {
            const ratio = inputSampleRate / targetSampleRate;
            const newLength = Math.floor(inputData.length / ratio);
            finalData = new Float32Array(newLength);
            for (let i = 0; i < newLength; i++) {
                const offset = Math.floor(i * ratio);
                const nextOffset = Math.floor((i + 1) * ratio);
                let sum = 0;
                let count = 0;
                for (let j = offset; j < nextOffset && j < inputData.length; j++) {
                    sum += inputData[j];
                    count++;
                }
                finalData[i] = count > 0 ? sum / count : 0;
            }
        }
        
        // Calculate volume for visualization
        let sum = 0;
        for (let i = 0; i < finalData.length; i++) {
             sum += finalData[i] * finalData[i];
        }
        const rms = Math.sqrt(sum / finalData.length);
        setAudioLevel(Math.min(rms * 5, 1)); 

        // Gain
        const gain = 1.0;
        const pcmData = new Int16Array(finalData.length);
        let pcmSumSq = 0;
        for (let i = 0; i < finalData.length; i++) {
             let s = finalData[i] * gain;
             s = Math.max(-1, Math.min(1, s));
             pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
             pcmSumSq += pcmData[i] * pcmData[i];
        }
        
        // Calculate PCM RMS (Integer based, matching backend)
        const currentPcmRms = Math.sqrt(pcmSumSq / pcmData.length);
        setPcmRms(currentPcmRms);

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
    setPcmRms(0);
  }, []);

  const playAudioChunk = useCallback((base64Data: string) => {
      // Ensure we have an audio context for playback even if not listening
      if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
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
        console.log(`Received Audio Chunk: ${float32Data.length} samples. Duration at 24k: ${(float32Data.length/24000).toFixed(3)}s, at 16k: ${(float32Data.length/16000).toFixed(3)}s`);
        for (let i = 0; i < int16Data.length; i++) {
            float32Data[i] = int16Data[i] / 32768.0;
        }

        // Gemini Live Audio is typically 24kHz, but preview might be 16kHz?
        // If it sounds high-pitched/fast, lower this. If low-pitched/slow, raise it.
        const buffer = ctx.createBuffer(1, float32Data.length, 24000); 
        buffer.copyToChannel(float32Data, 0);

        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(outputDestRef.current);
        
        const currentTime = ctx.currentTime;
        // Jitter Buffer: If we drift behind (underrun), reset to now + safety margin
        // Increased to 0.5s to fix "choppy" audio reports
        if (nextStartTimeRef.current < currentTime) {
            nextStartTimeRef.current = currentTime + 0.5; 
        }
        
        const startTime = nextStartTimeRef.current;
        source.start(startTime);
        nextStartTimeRef.current += buffer.duration;
      } catch (e) {
          console.error("Error playing audio chunk", e);
      }
  }, []);

  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  return { isListening, audioLevel, pcmRms, startListening, stopListening, playAudioChunk };
};