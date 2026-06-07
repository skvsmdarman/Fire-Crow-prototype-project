export interface DashboardMetrics {
  totalJobs: number;
  activeJobs: number;
  criticalFindings: number;
  highFindings: number;
  mediumFindings: number;
  lowFindings: number;
  posture: string;
  riskScore: number | null;
}
