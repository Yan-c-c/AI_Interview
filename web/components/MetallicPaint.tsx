"use client";

import type { CSSProperties } from "react";
import styles from "./MetallicPaint.module.css";

type MetallicPaintProps = {
  imageSrc: string;
  seed?: number;
  scale?: number;
  patternSharpness?: number;
  noiseScale?: number;
  speed?: number;
  liquid?: number;
  mouseAnimation?: boolean;
  brightness?: number;
  contrast?: number;
  refraction?: number;
  blur?: number;
  chromaticSpread?: number;
  fresnel?: number;
  angle?: number;
  waveAmplitude?: number;
  distortion?: number;
  contour?: number;
  lightColor?: string;
  darkColor?: string;
  tintColor?: string;
  className?: string;
  "aria-label"?: string;
};

export default function MetallicPaint({
  imageSrc,
  seed = 42,
  scale = 4,
  speed = 0.3,
  brightness = 2,
  contrast = 0.5,
  blur = 0.015,
  chromaticSpread = 2,
  angle = 0,
  waveAmplitude = 1,
  distortion = 1,
  tintColor = "#feb3ff",
  className = "",
  "aria-label": ariaLabel,
}: MetallicPaintProps) {
  const duration = Math.max(1.8, 4.8 / Math.max(speed, 0.05));
  const style = {
    "--metal-mask": `url("${imageSrc}")`,
    "--metal-speed": `${duration + (seed % 7) * 0.08}s`,
    "--metal-brightness": String(Math.max(0.6, brightness * 0.8)),
    "--metal-contrast": String(Math.max(0.75, 1 + contrast * 0.16)),
    "--metal-tint": tintColor,
    "--metal-angle": `${angle}deg`,
    "--metal-blur": `${Math.max(0, blur * 18)}px`,
    "--metal-scale": String(scale),
    "--metal-wave": String(waveAmplitude),
    "--metal-spread": String(chromaticSpread),
    "--metal-distortion": String(distortion),
  } as CSSProperties;

  return (
    <span
      className={`${styles.paint} ${className}`}
      style={style}
      role={ariaLabel ? "img" : undefined}
      aria-label={ariaLabel}
      aria-hidden={ariaLabel ? undefined : true}
    />
  );
}
