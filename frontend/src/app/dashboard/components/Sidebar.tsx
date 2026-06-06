"use client";

import React from "react";
import { motion } from "framer-motion";
import { FileText, Home, LucideIcon, Search, Settings, ShieldCheck } from "lucide-react";
import styles from "../page.module.css";

export type Section = "home" | "audits" | "findings" | "reports" | "settings";

interface SidebarProps {
  activeSection: Section;
  setActiveSection: (section: Section) => void;
  username: string;
  userId: string;
}

const sections: { id: Section; label: string; mobileLabel: string; icon: LucideIcon; ariaLabel: string }[] = [
  { id: "home", label: "Home", mobileLabel: "Home", icon: Home, ariaLabel: "Open dashboard home" },
  { id: "audits", label: "Audits", mobileLabel: "Audits", icon: ShieldCheck, ariaLabel: "Open audit operations" },
  { id: "findings", label: "Findings", mobileLabel: "Findings", icon: Search, ariaLabel: "Open findings" },
  { id: "reports", label: "Reports", mobileLabel: "Reports", icon: FileText, ariaLabel: "Open reports" },
  { id: "settings", label: "Settings", mobileLabel: "Settings", icon: Settings, ariaLabel: "Open settings" },
];

export default function Sidebar({
  activeSection,
  setActiveSection,
  username,
  userId,
}: SidebarProps) {
  return (
    <aside className={`${styles.sidebar} fc-dashboard-sidebar`}>
      <div className={`${styles.brandBlock} fc-dashboard-brand`}>
        <div className={styles.brandMark}>FC</div>
        <div>
          <div className={styles.brandName}>Fire Crow</div>
          <div className={styles.brandSubtitle}>FCv1 Security Audit</div>
        </div>
      </div>

      <nav className={`${styles.navStack} fc-dashboard-bottom-nav`} aria-label="Primary navigation">
        {sections.map((section) => {
          const Icon = section.icon;
          const isActive = activeSection === section.id;
          return (
            <button
              key={section.id}
              className={[
                styles.navItem,
                "fc-dashboard-tab",
                isActive ? styles.navItemActive : "",
                isActive ? "fc-dashboard-tab-active" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              type="button"
              aria-label={section.ariaLabel}
              aria-current={isActive ? "page" : undefined}
              onClick={() => setActiveSection(section.id)}
              style={{ position: "relative" }}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTabIndicator"
                  className={styles.activeIndicator}
                  transition={{
                    type: "spring",
                    stiffness: 380,
                    damping: 30,
                  }}
                />
              )}
              <span className={styles.navItemContent}>
                <Icon
                  size={16}
                  className={[
                    styles.navIcon,
                    "fc-dashboard-tab-icon",
                    isActive ? styles.navIconActive : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                />
                <span className={`${styles.navLabel} fc-dashboard-tab-label`}>
                  <span className="fc-dashboard-desktop-label">{section.label}</span>
                  <span className="fc-dashboard-mobile-label">{section.mobileLabel}</span>
                </span>
              </span>
            </button>
          );
        })}
      </nav>

      <div className={`${styles.workspaceCard} fc-dashboard-workspace-card`}>
        <div className={styles.authCardAccent} />
        <div className={styles.sectionKicker}>Workspace</div>
        <div className={styles.workspaceName}>{username || "Not connected"}</div>
        <div className={styles.workspaceId}>{userId || "Connect to access audit history"}</div>
      </div>
    </aside>
  );
}
