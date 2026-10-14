"use client";

import { useCallback, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api/resumeEvaluation";

interface UseVoiceRecorderProps {
  onTranscript: (text: string) => void;
}

export function useVoiceRecorder({ onTranscript }: UseVoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("当前浏览器不支持麦克风录音。");
      return;
    }
    if (isRecording) return;
    setError(null);
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
    };
    recorderRef.current = recorder;
    recorder.start();
    setIsRecording(true);
  }, [isRecording]);

  const stopRecordingAndTranscribe = useCallback(async () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    setError(null);
    const stopped = new Promise<void>((resolve) => {
      const originalOnStop = recorder.onstop;
      recorder.onstop = (event) => {
        originalOnStop?.call(recorder, event);
        resolve();
      };
    });
    recorder.stop();
    setIsRecording(false);
    await stopped;
    const webm = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
    if (!webm.size) {
      setError("没有录到有效音频。");
      return;
    }
    setIsRecognizing(true);
    try {
      const pcm = await webmToPcm16k(webm);
      const formData = new FormData();
      formData.append("audio", pcm, "answer.pcm");
      formData.append("format", "pcm");
      formData.append("rate", "16000");
      const response = await fetch(`${API_BASE_URL}/api/interview-audio/stt`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail?.message || payload.message || "语音识别失败");
      }
      const text = String(payload.text || "").trim();
      if (text) onTranscript(text);
      else setError("未识别到有效文字。");
    } catch (event) {
      setError(event instanceof Error ? event.message : "语音识别失败");
    } finally {
      setIsRecognizing(false);
    }
  }, [onTranscript]);

  const cancelRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    recorder?.stream.getTracks().forEach((track) => track.stop());
    recorderRef.current = null;
    chunksRef.current = [];
    setIsRecording(false);
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecording) void stopRecordingAndTranscribe();
    else void startRecording();
  }, [isRecording, startRecording, stopRecordingAndTranscribe]);

  return {
    isSupported: typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined",
    isRecording,
    isRecognizing,
    error,
    startRecording,
    stopRecordingAndTranscribe,
    cancelRecording,
    toggleRecording,
  };
}

async function webmToPcm16k(webmBlob: Blob): Promise<Blob> {
  const arrayBuffer = await webmBlob.arrayBuffer();
  const AudioContextClass = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextClass) throw new Error("当前浏览器不支持音频解码。");
  const audioContext = new AudioContextClass();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  await audioContext.close();

  const offlineContext = new OfflineAudioContext(1, Math.ceil(audioBuffer.duration * 16000), 16000);
  const source = offlineContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineContext.destination);
  source.start();
  const rendered = await offlineContext.startRendering();
  const channel = rendered.getChannelData(0);
  const pcm = new Int16Array(channel.length);
  for (let index = 0; index < channel.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, channel[index] || 0));
    pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return new Blob([pcm.buffer], { type: "audio/pcm" });
}
