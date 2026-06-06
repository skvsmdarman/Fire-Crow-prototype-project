"use client";

import React from "react";
import { motion } from "framer-motion";
import { LayoutGrid, FileText, Cpu, Settings, LucideIcon } from "lucide-react";
import styles from "../page.module.css";

export type Section = "operations" | "reports" | "agents" | "settings";

interface SidebarProps {
  activeSection: Section;
  setActiveSection: (section: Section) => void;
  username: string;
  userId: string;
}

const sections: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: "operations", label: "Operations", icon: LayoutGrid },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "agents", label: "Agents", icon: Cpu },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function Sidebar({
  activeSection,
  setActiveSection,
  username,
  userId,
}: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brandBlock}>
        <div className={styles.brandMark}>FC</div>
        <div>
          <div className={styles.brandName}>FireCrow</div>
          <div className={styles.brandSubtitle}>FCv1 Security Audit</div>
        </div>
      </div>

      <nav className={styles.navStack} aria-label="Primary navigation">
        {sections.map((section) => {
          const Icon = section.icon;
          const isActive = activeSection === section.id;
          return (
            <button
              key={section.id}
              className={[
                styles.navItem,
                isActive ? styles.navItemActive : "",
              ]
                .filter(Boolean)
                .join(" ")}
              type="button"
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
                    isActive ? styles.navIconActive : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                />
                <span className={styles.navLabel}>{section.label}</span>
              </span>
            </button>
          );
        })}
      </nav>

      <div className={styles.workspaceCard}>
        <div className={styles.authCardAccent} />
        <div className={styles.sectionKicker}>Workspace</div>
        <div className={styles.workspaceName}>{username || "Not connected"}</div>
        <div className={styles.workspaceId}>{userId || "Connect to access audit history"}</div>
      </div>
    </aside>
  );
}
