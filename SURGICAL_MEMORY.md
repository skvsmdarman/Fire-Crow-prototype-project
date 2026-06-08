# Fire Crow Surgical Memory

## 1. Global Bucket Cleaner (R2) – Delete nothing cross‑tenant
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Delete objects from a shared bucket without filtering by tenant/job ID.
- 📖 LESSON: Destructive operations must be scoped to the current tenant/job.

## 2. Token Revocation – Fail closed, no in‑memory fallback
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Fall back to in-memory storage for shared state in multi‑instance setups.
- 📖 LESSON: Redis is mandatory for production. Fail closed when it’s down.

## 3. Dead Celery Worker – Check heartbeat, fallback to background threads
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Assume that because Redis is reachable, the worker is alive.
- 📖 LESSON: Implement worker heartbeats and fallback to limited BackgroundTasks.

## 4. User Dockerfile Builds – Block arbitrary user‑supplied base images
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Build or run arbitrary Dockerfiles from untrusted sources.
- 📖 LESSON: Use only pre‑approved base images and read‑only mounts.

## 5. Silent Email Failure – Update database status and error message on failure
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Ignore boolean returns from critical side effects.
- 📖 LESSON: Always update job status and error messages when delivery fails.

## 6. Unlimited BackgroundTasks – Limit concurrent threads and reject if queue is full
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Allow unlimited concurrent background tasks in a shared environment.
- 📖 LESSON: Use semaphores to limit concurrency and reject when limit reached.

## 7. Unlimited SSE Connections – Limit concurrent SSE lines per user/IP
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Allow unlimited persistent connections per user.
- 📖 LESSON: Rate‑limit SSE connections and add idle timeouts.

## 8. No AI Cost Budget – Decrement budget, reject when empty
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Call paid APIs without checking remaining budget.
- 📖 LESSON: Always decrement budget and skip if exhausted.

## 9. No Email Validation – Reject bad/unverified email formats
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Accept any string as an email address.
- 📖 LESSON: Use a proper validation library before storing emails.

## 10. Branch Creation Race – Handle GitHub 422, retry with dynamic suffix
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Assume a branch name is unique; handle 422 with a fallback.
- 📖 LESSON: Always verify existing branch SHA and generate new name if mismatched.

---

# PART 2: HACKATHON SURGICAL FEATURES

## Feature A: Verified Remediation PR
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Merge a remediation PR without validating that original findings are no longer present.
- 📖 LESSON: Use clean temporary branches and runtime verification suite to check regression of original finding IDs.

## Feature B: Dynamic Vulnerability Attack Path Graph
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Rely on basic flat tables to visualize complex multi-stage vulnerability chains.
- 📖 LESSON: Use React Flow with dynamic node mapping to render clear, interactive topological representations of CVE pathways.

## Feature C: Real‑time SSE Leaderboard
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Require users to refresh the dashboard to see global security scoreboard updates.
- 📖 LESSON: Stream security score changes in real time using Server-Sent Events (SSE) and animate transitions smoothly in the UI.

## Feature D: Inline AI Agent Chat Widget
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Direct users to a generic chatbot disconnected from the specific context of their current audit job.
- 📖 LESSON: Scope AI chat history and runtime retrieval to the selected finding and active workspace database logs.

## Feature E: Push Notifications (PWA)
- ✅ DONE (2026-06-08)
- ⚠️ NEVER: Leave users in the dark on audit completion when they navigate away from the application.
- 📖 LESSON: Implement fully standard PWA push notification subscriptions using VAPID keys, service workers, and background triggers.
