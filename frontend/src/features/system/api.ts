import { apiClient } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
import { RawSystemStatus } from "./types";

export async function getSystemStatus(): Promise<RawSystemStatus> {
  return apiClient.get<RawSystemStatus>(ENDPOINTS.system.status);
}
