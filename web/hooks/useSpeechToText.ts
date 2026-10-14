"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseSpeechToTextProps {
  onTranscript: (text: string) => void;
  lang?: string;
}

export function useSpeechToText({ onTranscript, lang = "zh-CN" }: UseSpeechToTextProps) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const keepListeningRef = useRef(false);
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("当前浏览器不支持语音识别。");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = lang;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event: any) => {
      let finalTranscript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        if (event.results[index].isFinal) {
          finalTranscript += event.results[index][0].transcript;
        }
      }
      if (finalTranscript.trim()) {
        onTranscriptRef.current(finalTranscript.trim());
      }
    };

    recognition.onerror = (event: any) => {
      if (event.error === "no-speech" || event.error === "aborted") return;
      setError(String(event.error || "语音识别失败"));
      keepListeningRef.current = false;
      setIsListening(false);
    };

    recognition.onend = () => {
      if (keepListeningRef.current) {
        try {
          recognition.start();
        } catch {
          keepListeningRef.current = false;
          setIsListening(false);
        }
      } else {
        setIsListening(false);
      }
    };

    recognitionRef.current = recognition;
    return () => {
      keepListeningRef.current = false;
      recognition.stop();
    };
  }, [lang]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListening) return;
    keepListeningRef.current = true;
    try {
      recognitionRef.current.start();
    } catch (event) {
      keepListeningRef.current = false;
      setError(event instanceof Error ? event.message : "语音识别启动失败");
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    keepListeningRef.current = false;
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) stopListening();
    else startListening();
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    error,
    isSupported: typeof window !== "undefined" && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition),
    startListening,
    stopListening,
    toggleListening,
  };
}
