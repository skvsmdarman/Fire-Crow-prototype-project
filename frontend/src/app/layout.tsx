import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono, Rajdhani } from "next/font/google";
import { ReactNode } from "react";
import "./globals.css";

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

const display = Rajdhani({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Fire Crow",
  description: "Authorization-first security orchestration console for Fire Crow.",
  icons: {
    icon: "/fire_crow_logo.png",
    apple: "/fire_crow_logo.png",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${display.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}
