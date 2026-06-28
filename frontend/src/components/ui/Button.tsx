import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", loading = false, className = "", children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`fc-button fc-button-${variant} ${className}`.trim()}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <span className="fc-button-spinner" aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  );
});
