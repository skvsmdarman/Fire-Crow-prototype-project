# Fire Crow Security Fixes Memory

## Issue 1: Global Bucket Cleaner
- ✅ FIXED (2026-06-09)
- ⚠️ NEVER: Delete objects from a shared bucket without filtering by tenant/job ID.
- 📖 Lesson: Destructive operations must be scoped to the current tenant/job.

## Issue 2: Token Revocation Without Redis
- ✅ FIXED
- ⚠️ NEVER: Fall back to in-memory storage for shared state in multi‑instance setups.
- 📖 Lesson: Redis is mandatory for production. Fail closed when it’s down.

## Issue 3: Dead Celery Worker
- ✅ FIXED
- ⚠️ NEVER: Assume that because Redis is reachable, the worker is alive.
- 📖 Lesson: Implement worker heartbeats and fallback to limited BackgroundTasks.

## Issue 4: User Dockerfile Builds
- ✅ FIXED
- ⚠️ NEVER: Build or run arbitrary Dockerfiles from untrusted sources.
- 📖 Lesson: Use only pre‑approved base images and read‑only mounts.

## Issue 5: Silent Email Failure
- ✅ FIXED
- ⚠️ NEVER: Ignore boolean returns from critical side effects.
- 📖 Lesson: Always update job status and error messages when delivery fails.

## Issue 6: Unlimited BackgroundTasks
- ✅ FIXED
- ⚠️ NEVER: Allow unlimited concurrent background tasks in a shared environment.
- 📖 Lesson: Use semaphores to limit concurrency and reject when limit reached.

## Issue 7: Unlimited SSE Connections
- ✅ FIXED
- ⚠️ NEVER: Allow unlimited persistent connections per user.
- 📖 Lesson: Rate‑limit SSE connections and add idle timeouts.

## Issue 8: No AI Cost Budget
- ✅ FIXED
- ⚠️ NEVER: Call paid APIs without checking remaining budget.
- 📖 Lesson: Always decrement budget and skip if exhausted.

## Issue 9: No Email Validation
- ✅ FIXED
- ⚠️ NEVER: Accept any string as an email address.
- 📖 Lesson: Use a proper validation library before storing emails.

## Issue 10: Branch Creation Race
- ✅ FIXED
- ⚠️ NEVER: Assume a branch name is unique; handle 422 with a fallback.
- 📖 Lesson: Always verify existing branch SHA and generate new name if mismatched.

## Issue 11: LLM Isolation Policy
- ✅ FIXED (2026-06-09)
- ⚠️ NEVER: Use LLM output for report generation, remediation code, finding deduplication, or severity scoring.
- 📖 Lesson: Keep LLM use optional, cosmetic, and feature-flagged for user-facing hints only.

## Frontend Sync with Backend Features
- ✅ DOCUMENTED (2026-06-09)
- ⚠️ NEVER: Add backend features without updating frontend types, contracts, and API docs at the same time.
- 📖 Lesson: Keep the dashboard, OpenAPI artifact, and response payloads in lockstep with backend behavior.

## Lessons Learned (The Golden Rules)
1. **Scope all destructive operations** – never touch data outside the current tenant/job.
2. **Redis is not optional in multi‑instance** – no in‑memory fallbacks for shared state.
3. **Never trust user‑supplied build instructions** – sandboxes must use read‑only, pre‑approved images.
4. **Every side effect must be reported** – if email fails, the user must know.
5. **Always limit concurrency** – background tasks, SSE connections, and external API calls.
6. **Budget every paid service** – AI, email, storage – and stop when empty.
7. **Validate every input** – especially emails, URLs, and branch names.
