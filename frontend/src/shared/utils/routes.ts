export const ROUTES = {
  landing: "/",
  signin: "/signin",
  dashboard: "/dashboard",
  terms: "/terms",
  privacy: "/privacy",
};

export function getDashboardUrl(workspaceName?: string): string {
  const ws = (workspaceName || "workspace").trim();
  return `${ROUTES.dashboard}?workspace=${encodeURIComponent(ws)}`;
}
