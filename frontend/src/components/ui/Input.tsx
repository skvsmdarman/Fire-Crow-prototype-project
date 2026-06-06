"use client";

import React, { ForwardedRef, forwardRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import styles from "./Input.module.css";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  icon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  error?: string;
}

const Input = forwardRef(
  (
    { label, icon, rightIcon, error, type = "text", className, id, ...props }: InputProps,
    ref: ForwardedRef<HTMLInputElement>
  ) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === "password";
    const inputType = isPassword && showPassword ? "text" : type;

    const wrapperClass = [
      styles.inputWrapper,
      error ? styles.inputError : "",
      icon ? styles.hasLeftIcon : "",
      isPassword || rightIcon ? styles.hasRightIcon : "",
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div className={[styles.container, className].filter(Boolean).join(" ")}>
        {label && (
          <label htmlFor={id} className={styles.label}>
            {label}
          </label>
        )}
        <div className={wrapperClass}>
          {icon && <span className={styles.leftIcon}>{icon}</span>}
          <input
            id={id}
            ref={ref}
            type={inputType}
            className={styles.input}
            aria-invalid={!!error}
            {...props}
          />
          {isPassword ? (
            <button
              type="button"
              className={styles.rightIconButton}
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          ) : rightIcon ? (
            <span className={styles.rightIcon}>{rightIcon}</span>
          ) : null}
        </div>
        {error && <span className={styles.errorMessage}>{error}</span>}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
