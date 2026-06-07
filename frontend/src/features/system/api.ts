import { apiClient } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
import { SystemStatus } from "./types";

export async function getSystemStatus(): Promise<SystemStatus> {
  return apiClient.get<SystemStatus>(ENDPOINTS.system.status);
}
