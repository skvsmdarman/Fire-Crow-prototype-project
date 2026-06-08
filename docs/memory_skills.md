# Antigravity Memory & Context Management Skills

This document details how **Antigravity** manages knowledge, retrieves history, and coordinates context during execution. It outlines the hierarchy of memory sources and how to write and update artifacts for future reference.

---

## 1. Information Retrieval Hierarchy
To avoid redundant work, stale configurations, or conflicting updates, Antigravity uses a strict search hierarchy:
1. **Knowledge Items (KIs)** (Highest Priority)
2. **Conversation Logs**
3. **Fresh Research / Web Search** (Fallback)

---

## 2. The Knowledge Item (KI) System
Knowledge Items are curated, distilled summaries of specific repository topics, bug fixes, or setup instructions.
* **Location**: Found under `<appDataDir>\knowledge\`.
* **First Action**: Always check the KI summaries at the start of a session.
* **Verification**: Treat KIs as valuable historical snapshots, but cross-reference them with active codebase files to ensure paths, APIs, and schemas haven't evolved.

---

## 3. Conversation Logs & Overview Transcripts
When KIs are insufficient or when specific past details are referenced:
* **Location**: Found under `<appDataDir>\brain\<conversation-id>\.system_generated\logs\overview.txt`.
* **Usage**: Parse conversation logs to understand user intent, historical choices, and unresolved tasks from previous sessions.

---

## 4. Artifact & Scratchpad Guidelines
* **Scratchpads**: Store temporary scripts, test scripts, or one-off code outputs under `<appDataDir>\brain\<conversation-id>\scratch\`.
* **Artifacts**: Use markdown artifacts (`.md` files) to present structured information (e.g., plans, walkthroughs, reports) in a readable format.
* **Formatting Conventions**:
  * **Alerts**: Use GitHub-style warnings and notes (`> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]`).
  * **Diffs**: Display edits in diff blocks with standard `+` (additions) and `-` (deletions).
  * **File Links**: Link directly to files and line ranges (e.g., `[basename.py](file:///absolute/path/to/basename.py#L100-L150)`) without using backticks on the link text.
  * **Carousels**: Use four backticks with the `carousel` language identifier to group related images, diagrams, or code blocks sequentially.

---
*Documentation last updated: June 08, 2026*
