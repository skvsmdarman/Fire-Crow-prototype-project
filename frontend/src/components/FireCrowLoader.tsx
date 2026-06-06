"use client";

import { useId } from "react";

import styles from "./FireCrowLoader.module.css";

interface FireCrowLoaderProps {
  className?: string;
  label?: string;
  size?: "sm" | "md" | "lg";
}

export default function FireCrowLoader({
  className,
  label = "Loading FireCrow",
  size = "md",
}: FireCrowLoaderProps) {
  const baseId = useId().replace(/:/g, "");
  const ringId = `${baseId}-ring`;
  const wingId = `${baseId}-wing`;
  const flameId = `${baseId}-flame`;

  return (
    <span className={[styles.loader, styles[size], className].filter(Boolean).join(" ")} aria-hidden="true">
      <svg className={styles.svg} viewBox="0 0 64 64" role="img" aria-label={label}>
        <defs>
          <linearGradient id={ringId} x1="8" x2="56" y1="12" y2="56" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffbf47" />
            <stop offset="55%" stopColor="#ff7d11" />
            <stop offset="100%" stopColor="#ff4d08" />
          </linearGradient>
          <linearGradient id={wingId} x1="18" x2="48" y1="24" y2="46" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#ffe0bc" stopOpacity="0.72" />
          </linearGradient>
          <linearGradient id={flameId} x1="26" x2="40" y1="10" y2="44" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fff5cf" />
            <stop offset="40%" stopColor="#ffd28f" />
            <stop offset="100%" stopColor="#ff7d11" />
          </linearGradient>
        </defs>
        <circle className={styles.ring} cx="32" cy="32" r="23" fill="none" stroke={`url(#${ringId})`} strokeWidth="2.5" />
        <path
          className={styles.wing}
          fill={`url(#${wingId})`}
          d="M17 39.5c6.5-10.5 14.6-16.5 24-17.5 4.9-.6 8.9.2 12 2.4-3.8.4-7.2 2-10.3 4.8-4.7 4.1-9.2 8.3-13.5 12.7-4 4-7.8 6.1-11.5 6.2-3.8.1-4.8-2.1-0.7-8.6z"
        />
        <path
          className={styles.flame}
          fill={`url(#${flameId})`}
          d="M31.9 11.5c3.8 4.2 8.1 6.8 8.1 12.1 0 5.7-4.4 9.8-8.1 14.4-4-4.1-8.1-8.7-8.1-14.4 0-5.3 4.1-8.5 8.1-12.1z"
        />
        <circle className={styles.spark} cx="40.5" cy="17.5" r="2.3" />
      </svg>
    </span>
  );
}
