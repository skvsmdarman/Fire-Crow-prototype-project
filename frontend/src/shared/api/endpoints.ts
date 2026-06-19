export const ENDPOINTS = {
  auth: {
    policyContext: "/auth/policy-context",
    policyEvents: "/auth/policy-events",
    login: "/auth/login",
    register: "/auth/register",
    exchange: "/auth/exchange",
    me: "/auth/me",
    session: "/auth/session",
    logout: "/auth/logout",
  },
  audit: {
    submit: "/audit/submit",
    jobs: "/audit/jobs",
    job: (jobId: string) => "/audit/job/" + jobId,
    insight: (jobId: string) => "/audit/job/" + jobId + "/insight",
    report: (jobId: string) => "/audit/job/" + jobId + "/report",
    stream: (jobId: string) => "/audit/" + jobId + "/stream",
    graph: (jobId: string) => "/audit/job/" + jobId + "/graph",
    cancel: (jobId: string) => "/audit/job/" + jobId + "/cancel",
  },
  chat: {
    ask: "/chat/ask",
  },
  leaderboard: {
    list: "/leaderboard",
  },
  push: {
    vapidPublicKey: "/push/vapid-public-key",
    subscribe: "/push/subscribe",
  },
  system: {
    status: "/system/status",
    dbStats: "/system/database/stats",
    dbHousekeeping: "/system/database/housekeeping",
  },
};
