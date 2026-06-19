import React from 'react';
import Link from 'next/link';
import styles from './BrandLogo.module.css';
import { PRODUCT_NAME, PRODUCT_TAGLINE } from '../shared/config/app';

interface BrandLogoProps {
  className?: string;
  isLink?: boolean;
}

export default function BrandLogo({ className = '', isLink = true }: BrandLogoProps) {
  const content = (
    <>
      <span className={styles.brandMark}>FC</span>
      <span className={styles.brandText}>
        <strong>{PRODUCT_NAME}</strong>
        <small>{PRODUCT_TAGLINE}</small>
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
