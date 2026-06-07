export class APIError extends Error {
  status?: number;
  code?: string;
  requestId?: string;

  constructor(message: string, status?: number, code?: string, requestId?: string) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}
