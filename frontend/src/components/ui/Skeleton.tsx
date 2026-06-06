"use client";

import React from "react";
import styles from "./Skeleton.module.css";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
}

export default function Skeleton({
  variant = "rectangular",
  width,
  height,
  className,
  style,
  ...props
}: SkeletonProps) {
  const customStyles: React.CSSProperties = {
    width: width !== undefined ? (typeof width === "number" ? `${width}px` : width) : undefined,
    height: height !== undefined ? (typeof height === "number" ? `${height}px` : height) : undefined,
    ...style,
  };

  const skeletonClasses = [
    styles.skeleton,
    styles[variant],
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return <div className={skeletonClasses} style={customStyles} {...props} />;
}
