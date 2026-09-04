"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties, type ElementType } from "react";

type SplitTextProps = {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
  ease?: string;
  splitType?: "chars" | "words" | "lines" | "words, chars";
  from?: { opacity?: number; y?: number };
  to?: { opacity?: number; y?: number };
  threshold?: number;
  rootMargin?: string;
  textAlign?: CSSProperties["textAlign"];
  tag?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "p" | "span";
  onLetterAnimationComplete?: () => void;
  showCallback?: boolean;
};

function easingToCss(ease: string) {
  if (ease === "power3.out") return "cubic-bezier(0.22, 1, 0.36, 1)";
  if (ease === "power2.out") return "cubic-bezier(0.16, 1, 0.3, 1)";
  return ease.includes("cubic-bezier") ? ease : "cubic-bezier(0.22, 1, 0.36, 1)";
}

function splitText(text: string, splitType: SplitTextProps["splitType"]) {
  if (splitType === "words") {
    return text.split(/(\s+)/).filter(Boolean);
  }
  return Array.from(text);
}

export default function SplitText({
  text,
  className = "",
  delay = 50,
  duration = 1.25,
  ease = "power3.out",
  splitType = "chars",
  from = { opacity: 0, y: 40 },
  to = { opacity: 1, y: 0 },
  threshold = 0.1,
  rootMargin = "-100px",
  textAlign = "center",
  tag = "p",
  onLetterAnimationComplete,
}: SplitTextProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const tokens = useMemo(() => splitText(text, splitType), [text, splitType]);

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(motionQuery.matches);
    const handleChange = () => setReducedMotion(motionQuery.matches);
    motionQuery.addEventListener("change", handleChange);
    return () => motionQuery.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    if (reducedMotion) {
      setVisible(true);
      onLetterAnimationComplete?.();
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold, rootMargin },
    );
    observer.observe(element);
    const fallback = window.setTimeout(() => setVisible(true), 250);
    return () => {
      window.clearTimeout(fallback);
      observer.disconnect();
    };
  }, [onLetterAnimationComplete, reducedMotion, rootMargin, threshold]);

  useEffect(() => {
    if (!visible || reducedMotion) return;
    const timeout = window.setTimeout(() => {
      onLetterAnimationComplete?.();
    }, duration * 1000 + Math.max(0, tokens.length - 1) * delay);
    return () => window.clearTimeout(timeout);
  }, [delay, duration, onLetterAnimationComplete, reducedMotion, tokens.length, visible]);

  const Tag = tag as ElementType;
  const wrapperStyle: CSSProperties = {
    display: "inline-block",
    textAlign,
    whiteSpace: "normal",
    wordWrap: "break-word",
  };

  return (
    <Tag ref={ref} className={`split-parent ${className}`} style={wrapperStyle} aria-label={text}>
      <span aria-hidden="true">
        {tokens.map((token, index) => {
          const isSpace = /^\s+$/.test(token);
          const tokenStyle: CSSProperties = {
            display: isSpace ? "inline" : "inline-block",
            opacity: visible ? to.opacity ?? 1 : from.opacity ?? 0,
            transform: isSpace ? undefined : `translateY(${visible ? to.y ?? 0 : from.y ?? 40}px)`,
            transitionProperty: "opacity, transform",
            transitionDuration: `${duration}s`,
            transitionTimingFunction: easingToCss(ease),
            transitionDelay: `${index * delay}ms`,
            willChange: "opacity, transform",
          };
          return (
            <span key={`${token}-${index}`} style={tokenStyle}>
              {token}
            </span>
          );
        })}
      </span>
    </Tag>
  );
}
