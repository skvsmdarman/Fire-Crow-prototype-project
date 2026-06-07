import { apiClient } from "../../shared/api/client";
import { ENDPOINTS } from "../../shared/api/endpoints";
import { PolicyContext, AuthSessionPayload, UserMe } from "./types";

export async function getPolicyContext(): Promise<PolicyContext> {
  return apiClient.get<PolicyContext>(ENDPOINTS.auth.policyContext);
}

export async function loginUser(body: Record<string, unknown>): Promise<AuthSessionPayload> {
  return apiClient.post<AuthSessionPayload>(ENDPOINTS.auth.login, body);
}

export async function registerUser(body: Record<string, unknown>): Promise<AuthSessionPayload> {
  return apiClient.post<AuthSessionPayload>(ENDPOINTS.auth.register, body);
}

export async function exchangeCode(code: string): Promise<AuthSessionPayload> {
  return apiClient.post<AuthSessionPayload>(ENDPOINTS.auth.exchange, { code });
}

export async function getMe(): Promise<UserMe> {
  return apiClient.get<UserMe>(ENDPOINTS.auth.me);
}

export async function logoutUser(): Promise<void> {
  return apiClient.post<void>(ENDPOINTS.auth.logout);
}
