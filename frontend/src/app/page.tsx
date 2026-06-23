"use client";

import { useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  subscribeToAuthSession,
} from "../lib/authSession";
import Navbar from "../components/landing/Navbar";
import HeroSection from "../components/landing/HeroSection";
import CapabilitiesSection from "../components/landing/CapabilitiesSection";
import PipelineDemoSection from "../components/landing/PipelineDemoSection";
import AgentNetworkSection from "../components/landing/AgentNetworkSection";
import CtaSection from "../components/landing/CtaSection";
import Footer from "../components/Footer";
import styles from "./page.module.css";

export default function LandingPage() {
  const router = useRouter();
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );
  
  const isLoggedIn = session.hasDashboardSession;

  const handleEnter = () => {
    router.push(isLoggedIn ? "/dashboard" : "/signin");
  };

  return (
    <div className={styles.page}>
      <div className={styles.backdrop} />
      <div className={styles.noise} />
      
      <div className={styles.container}>
        <Navbar isLoggedIn={isLoggedIn} onEnter={handleEnter} />
        <HeroSection onEnter={handleEnter} />
        <CapabilitiesSection />
        <PipelineDemoSection />
        <AgentNetworkSection />
        <CtaSection isLoggedIn={isLoggedIn} onEnter={handleEnter} />
        <Footer />
      </div>
    </div>
  );
}
