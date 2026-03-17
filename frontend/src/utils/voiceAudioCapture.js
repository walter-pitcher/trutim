/**
 * Voice audio capture and streaming for wake word detection.
 * Captures microphone at browser sample rate, converts to PCM16, and sends to WebSocket.
 * Backend resamples to 16kHz internally.
 */

import { getUserMedia } from './mediaDevices';

const CHUNK_MS = 100;
const TARGET_SAMPLE_RATE = 16000;

/**
 * Convert Float32Array to PCM16 (Int16) bytes
 */
function float32ToPcm16(float32) {
  const pcm16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return new Uint8Array(pcm16.buffer);
}

/**
 * Simple downsampling: 48k -> 16k (factor 3), 44.1k -> 16k (factor ~2.76)
 */
function downsample(float32, fromRate, toRate) {
  if (fromRate === toRate) return float32;
  const ratio = fromRate / toRate;
  const outLength = Math.floor(float32.length / ratio);
  const out = new Float32Array(outLength);
  for (let i = 0; i < outLength; i++) {
    const srcIdx = i * ratio;
    const idx0 = Math.floor(srcIdx);
    const idx1 = Math.min(idx0 + 1, float32.length - 1);
    const frac = srcIdx - idx0;
    out[i] = float32[idx0] * (1 - frac) + float32[idx1] * frac;
  }
  return out;
}

/**
 * Encode Uint8Array to base64 (chunked to avoid stack overflow)
 */
function toBase64(bytes) {
  let binary = '';
  const chunkSize = 8192;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

/**
 * Start capturing microphone and streaming to the provided send function.
 * @param {Function} sendFn - (payload) => void, sends JSON or (bytes) => void for binary
 * @param {number} sampleRate - Browser's AudioContext sample rate (typically 48000 or 44100)
 * @returns {Promise<{ stop: Function }>} - Object with stop() to end capture
 */
export async function startVoiceCapture(sendFn, sampleRate = 48000) {
  const stream = await getUserMedia({ audio: true });
  const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate });
  const source = audioContext.createMediaStreamSource(stream);

  // ScriptProcessorNode is deprecated but widely supported; buffer 4096 at 48k ≈ 85ms
  const bufferSize = 4096;
  const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
  const gainNode = audioContext.createGain();
  gainNode.gain.value = 0; // Prevent mic feedback to speaker
  source.connect(processor);
  processor.connect(gainNode);
  gainNode.connect(audioContext.destination);

  const effectiveRate = audioContext.sampleRate;

  processor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    const resampled = downsample(input, effectiveRate, TARGET_SAMPLE_RATE);
    const pcm16 = float32ToPcm16(resampled);
    const base64 = toBase64(pcm16);
    sendFn({ type: 'audio_data', data: base64, sample_rate: TARGET_SAMPLE_RATE });
  };

  return {
    stop: () => {
      processor.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
    },
  };
}
