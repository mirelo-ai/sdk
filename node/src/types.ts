export class MireloError extends Error {
  readonly code: string;
  readonly httpStatus: number;

  constructor(message: string, code: string, httpStatus: number) {
    super(message);
    this.name = "MireloError";
    this.code = code;
    this.httpStatus = httpStatus;
  }
}

export interface MeResult {
  id: string;
  email: string;
  creditsAvailable: number;
  overageEnabled: boolean;
}

export interface PreflightResult {
  credits: number;
  estimatedMs: number;
}

export interface SyncResult {
  resultUrls: string[];
}

export type JobStatus =
  | { status: "processing"; progressPercent: number; estimatedCompletionAt: string }
  | { status: "succeeded"; resultUrls: string[] }
  | { status: "errored"; code: string; message: string; httpStatus: number };
