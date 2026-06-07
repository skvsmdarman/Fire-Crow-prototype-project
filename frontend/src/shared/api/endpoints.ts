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
    job: (jobId: string) => `/audit/job/${jobId}`,
    report: (jobId: string) => `/audit/job/${jobId}/report`,
    stream: (jobId: string) => `/audit/${jobId}/stream`,
  },
  system: {
    status: "/system/status",
  },
};
