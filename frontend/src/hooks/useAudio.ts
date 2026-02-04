import { useState, useEffect, useRef, useCallback } from 'react';

export const useAudio = () => {
  const [isListening, setIsListening] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [pcmRms, setPcmRms] = useState(0);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);  // For mic input (16kHz)
  const playbackContextRef = useRef<AudioContext | null>(null);  // For TTS playback (native rate)
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const playbackAnalyserRef = useRef<AnalyserNode | null>(null);
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
            echoCancellation: true,  // Enable to prevent agent hearing itself
            noiseSuppression: false,
            autoGainControl: false
        }
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
          sampleRate: 16000,
      });
      console.log("DEBUG: AudioContext Sample Rate:", audioContext.sampleRate);
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;
      
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      setAnalyser(analyser);

      const processor = audioContext.createScriptProcessor(2048, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const inputSampleRate = audioContext.sampleRate;
        const targetSampleRate = 16000;

        // Log sample rate mismatch (only once)
        if (!(processorRef.current as AudioNode & { hasLoggedRate?: boolean }).hasLoggedRate) {
          console.log(`[Audio] Input: ${inputSampleRate}Hz, Target: ${targetSampleRate}Hz, Ratio: ${inputSampleRate/targetSampleRate}`);
          (processorRef.current as AudioNode & { hasLoggedRate?: boolean }).hasLoggedRate = true;
        }

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
        
        // Calculate volume for visualization (Calculated in animation loop now)
        const pcmData = new Int16Array(finalData.length);
        let pcmSumSq = 0;
        for (let i = 0; i < finalData.length; i++) {
             let s = finalData[i] * 2.0; // Gain 2.0
             s = Math.max(-1, Math.min(1, s));
             pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
             pcmSumSq += pcmData[i] * pcmData[i];
        }
        
        // Calculate PCM RMS (Integer based, matching backend)
        const currentPcmRms = Math.sqrt(pcmSumSq / pcmData.length);
        setPcmRms(currentPcmRms);

        onAudioData(pcmData.buffer);
      };

      source.connect(analyser);
      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsListening(true);
      nextStartTimeRef.current = audioContext.currentTime;

    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  }, []);

  // Continuous animation loop for audio levels
  const lastLevelRef = useRef(0);
  useEffect(() => {
    let animationFrame: number;
    
    const updateLevels = () => {
      let currentMax = 0;

      // Check Mic
      if (analyserRef.current) {
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteTimeDomainData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          const v = (dataArray[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        // Significantly increased multiplier for mic (120 -> 180) for highly dramatic user response
        const level = rms > 0.01 ? rms * 180 : 0; 
        currentMax = Math.max(currentMax, level);
      }

      // Check Playback
      if (playbackAnalyserRef.current) {
        const dataArray = new Uint8Array(playbackAnalyserRef.current.frequencyBinCount);
        playbackAnalyserRef.current.getByteTimeDomainData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          const v = (dataArray[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        // Increased playback multiplier to 15
        const level = rms > 0.005 ? rms * 15 : 0; 
        currentMax = Math.max(currentMax, level);
      }

      // Extremely heavy smoothing (0.025) for a "high-viscosity" liquid feel.
      // This preserves the peak amplitude but forces the sphere to transition 
      // there much more slowly and smoothly, eliminating eye strain.
      const smoothedLevel = lastLevelRef.current * 0.975 + Math.min(currentMax, 1.0) * 0.025;
      lastLevelRef.current = smoothedLevel;

      setAudioLevel(smoothedLevel);
      animationFrame = requestAnimationFrame(updateLevels);
    };

    updateLevels();
    return () => cancelAnimationFrame(animationFrame);
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
    if (analyserRef.current) {
        analyserRef.current.disconnect();
        analyserRef.current = null;
    }
    setAnalyser(null);
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
    // Note: Keep playbackContextRef alive for TTS playback
    setIsListening(false);
    setAudioLevel(0);
    setPcmRms(0);
  }, []);

  // Kokoro TTS sample rate
  const TTS_SAMPLE_RATE = 24000;
  const nextPlayTimeRef = useRef<number>(0);

  // Get or create playback context (separate from mic context)
  const getPlaybackContext = useCallback(() => {
      if (!playbackContextRef.current) {
          playbackContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
          console.log(`[Audio] Playback context created at ${playbackContextRef.current.sampleRate}Hz`);
          
          const playbackAnalyser = playbackContextRef.current.createAnalyser();
          playbackAnalyser.fftSize = 256;
          playbackAnalyserRef.current = playbackAnalyser;
          playbackAnalyser.connect(playbackContextRef.current.destination);
          
          nextPlayTimeRef.current = playbackContextRef.current.currentTime;
      }
      return playbackContextRef.current;
  }, []);

  // Reset audio timing for new turn
  const resetAudioPlayback = useCallback(() => {
      const ctx = playbackContextRef.current;
      if (ctx) {
          nextPlayTimeRef.current = ctx.currentTime + 0.1;
      }
      console.log('[Audio] Reset for new turn');
  }, []);

  const stopAudioPlayback = useCallback(() => {
      const ctx = playbackContextRef.current;
      if (ctx) {
          // We can't easily "cancel" already scheduled AudioBufferSourceNodes 
          // without keeping track of them all, but we can suspend/resume the context
          // or just close and recreate it for a "hard stop".
          // Re-creating the context is the most reliable way to kill all pending audio.
          playbackContextRef.current.close().catch(() => {});
          playbackContextRef.current = null;
          nextPlayTimeRef.current = 0;
          console.log('[Audio] Playback stopped and context cleared');
      }
  }, []);

  // No-op for compatibility
  const playAccumulatedAudio = useCallback(() => {}, []);

  const playAudioChunk = useCallback((base64Data: string) => {
      try {
        const ctx = getPlaybackContext();

        const binaryString = window.atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const int16Data = new Int16Array(bytes.buffer);
        const float32Data = new Float32Array(int16Data.length);
        
        for (let i = 0; i < int16Data.length; i++) {
            const sample = int16Data[i] / 32768.0;
            float32Data[i] = sample;
        }
        // Create buffer at TTS sample rate
        const buffer = ctx.createBuffer(1, float32Data.length, TTS_SAMPLE_RATE);
        buffer.copyToChannel(float32Data, 0);

        const source = ctx.createBufferSource();
        source.buffer = buffer;
        if (playbackAnalyserRef.current) {
            source.connect(playbackAnalyserRef.current);
        } else {
            source.connect(ctx.destination);
        }

        // Schedule playback
        const currentTime = ctx.currentTime;
        if (nextPlayTimeRef.current < currentTime) {
            nextPlayTimeRef.current = currentTime + 0.01;
        }

        source.start(nextPlayTimeRef.current);
        nextPlayTimeRef.current += buffer.duration;

        console.log(`[Audio] Playing ${int16Data.length} samples (${(int16Data.length/TTS_SAMPLE_RATE).toFixed(2)}s), ${len} bytes`);
      } catch (e) {
          console.error("Error playing audio chunk", e);
      }
  }, [getPlaybackContext]);

  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  const getPlaybackRemainingTime = useCallback(() => {
    if (!playbackContextRef.current) return 0;
    const remaining = nextPlayTimeRef.current - playbackContextRef.current.currentTime;
    return Math.max(0, remaining);
  }, []);

  return { isListening, audioLevel, pcmRms, analyser, startListening, stopListening, playAudioChunk, resetAudioPlayback, playAccumulatedAudio, getPlaybackRemainingTime, stopAudioPlayback };
};