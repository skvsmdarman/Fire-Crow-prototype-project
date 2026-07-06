import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono, Rajdhani } from "next/font/google";
import { ReactNode } from "react";
import { AuthProvider } from "../lib/auth-context";
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
  title: "Fire Crow — AI Security Review",
  description: "Automated code security scanning with clear findings and client-ready reports. Built by Nova Devs.",
  icons: {
    icon: "/fire_crow_logo.png",
    apple: "/fire_crow_logo.png",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${display.variable} ${mono.variable}`}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
