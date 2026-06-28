import type { Metadata, Viewport } from "next";
import { DM_Sans, JetBrains_Mono, Rajdhani } from "next/font/google";
import "./globals.css";
import "./mobile-pwa.css";
import { ToastProvider } from "../components/ui/Toast";
import PWARegister from "../components/PWARegister";

const dmSans = DM_Sans({
  variable: "--font-body",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const rajdhani = Rajdhani({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["600", "700"],
});

export const metadata: Metadata = {
  applicationName: "Fire Crow",
  title: "Fire Crow FCv1",
  description:
    "Authorization-only security audit operations for SaaS repositories, controlled sandbox validation, CVSS scoring, and founder-ready remediation reports.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/icons/firecrow-icon.svg",
    shortcut: "/icons/firecrow-icon.svg",
    apple: "/icons/firecrow-icon.svg",
  },
  appleWebApp: {
    capable: true,
    title: "Fire Crow",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#050609",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${dmSans.variable} ${jetBrainsMono.variable} ${rajdhani.variable}`} data-scroll-behavior="smooth">
      <body>
        <ToastProvider>
          {children}
          <PWARegister />
        </ToastProvider>
      </body>
    </html>
  );
}
