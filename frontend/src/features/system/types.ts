export interface SystemStatus {
  status: string;
  worker_status: string;
  tasks_queued: number;
  tasks_running: number;
  scanners_available: string[];
  active_sandboxes: number;
  celery_active: boolean;
  debug?: boolean;
  sandbox_mode?: boolean;
  integrations?: Record<string, unknown>;
}
