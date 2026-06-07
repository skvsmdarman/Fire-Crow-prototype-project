import React from 'react';
import Link from 'next/link';
import styles from './BrandLogo.module.css';

interface BrandLogoProps {
  className?: string;
  isLink?: boolean;
}

export default function BrandLogo({ className = '', isLink = true }: BrandLogoProps) {
  const content = (
    <>
      <span className={styles.brandMark}>FC</span>
      <span className={styles.brandText}>
        <strong>Fire Crow</strong>
        <small>FCv1 security audit</small>
      </span>
    </>
  );

  const combinedClassName = `${styles.brand} ${className}`.trim();

  if (isLink) {
    return (
      <Link href="/" className={combinedClassName}>
        {content}
      </Link>
    );
  }

  return (
    <div className={combinedClassName}>
      {content}
    </div>
  );
}
