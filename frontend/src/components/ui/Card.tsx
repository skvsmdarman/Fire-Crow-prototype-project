"use client";

import React, { ForwardedRef, forwardRef } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import styles from "./Card.module.css";

export interface CardProps extends Omit<HTMLMotionProps<"div">, "ref" | "children"> {
  hoverLift?: boolean;
  interactive?: boolean;
  glow?: boolean;
  variant?: "surface" | "surfaceAlt" | "glass" | "glowing";
  children?: React.ReactNode;
}

const Card = forwardRef(
  (
    {
      children,
      className,
      hoverLift = false,
      interactive = false,
      glow = false,
      variant = "surface",
      ...props
    }: CardProps,
    ref: ForwardedRef<HTMLDivElement>
  ) => {
    const classNames = [
      styles.card,
      styles[variant],
      hoverLift ? styles.hoverLift : "",
      glow ? styles.glow : "",
      interactive ? styles.interactive : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <motion.div
        ref={ref}
        className={classNames}
        whileHover={interactive ? { scale: 1.01, y: hoverLift ? -3 : 0 } : undefined}
        whileTap={interactive ? { scale: 0.99 } : undefined}
        transition={{
          type: "spring",
          stiffness: 350,
          damping: 18,
        }}
        {...props}
      >
        {glow && <span className={styles.glowBorder} />}
        <div className={styles.content}>{children}</div>
      </motion.div>
    );
  }
);

Card.displayName = "Card";

export default Card;
