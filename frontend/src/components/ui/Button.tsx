"use client";

import React, { ForwardedRef, forwardRef } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import styles from "./Button.module.css";

export interface ButtonProps extends Omit<HTMLMotionProps<"button">, "ref" | "children"> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "launch";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children?: React.ReactNode;
}

const Button = forwardRef(
  (
    {
      children,
      className,
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      ...props
    }: ButtonProps,
    ref: ForwardedRef<HTMLButtonElement>
  ) => {
    const classNames = [
      styles.button,
      styles[variant],
      styles[size],
      loading ? styles.loading : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <motion.button
        ref={ref}
        className={classNames}
        disabled={disabled || loading}
        whileHover={{
          scale: disabled || loading ? 1 : 1.02,
          y: disabled || loading ? 0 : -2,
        }}
        whileTap={{
          scale: disabled || loading ? 1 : 0.97,
        }}
        transition={{
          type: "spring",
          stiffness: 400,
          damping: 15,
        }}
        {...props}
      >
        {loading ? (
          <span className={styles.spinnerWrapper} aria-live="polite">
            <span className={styles.spinner} />
            {children}
          </span>
        ) : (
          children
        )}
      </motion.button>
    );
  }
);

Button.displayName = "Button";

export default Button;
