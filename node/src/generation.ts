import type { HttpConfig } from "./http.js";
import { httpRequest } from "./http.js";
import type { JobStatus, PreflightResult, SyncResult } from "./types.js";
import { MireloError } from "./types.js";
import type { Video } from "./video.js";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class Job {
  readonly jobId: string;
  readonly estimatedMs: number;
  readonly jobUrl: string;

  private readonly _basePath: string;
  private readonly _config: HttpConfig;

  constructor(
    jobId: string,
    estimatedMs: number,
    jobUrl: string,
    basePath: string,
    config: HttpConfig,
  ) {
    this.jobId = jobId;
    this.estimatedMs = estimatedMs;
    this.jobUrl = jobUrl;
    this._basePath = basePath;
    this._config = config;
  }

  async status(): Promise<JobStatus> {
    const raw = await httpRequest<{
      status: string;
      progress_percent?: number;
      estimated_completion_at?: string;
      result?: { result_urls: string[] };
      error?: { code: string; message: string; http_status: number };
    }>(this._config, "GET", `${this._config.baseUrl}${this._basePath}/jobs/${this.jobId}`);

    if (raw.status === "processing") {
      return {
        status: "processing",
        progressPercent: raw.progress_percent ?? 0,
        estimatedCompletionAt: raw.estimated_completion_at ?? "",
      };
    }
    if (raw.status === "succeeded") {
      return {
        status: "succeeded",
        resultUrls: raw.result?.result_urls ?? [],
      };
    }
    if (raw.status === "errored") {
      return {
        status: "errored",
        code: raw.error?.code ?? "generation_failed",
        message: raw.error?.message ?? "Generation failed",
        httpStatus: raw.error?.http_status ?? 502,
      };
    }
    throw new MireloError(`Unexpected job status: ${raw.status}`, "server_error", 500);
  }

  async wait({ pollIntervalMs = 500 }: { pollIntervalMs?: number } = {}): Promise<SyncResult> {
    const timeoutMs = Math.max(this.estimatedMs * 3, 5 * 60 * 1000);
    const deadline = Date.now() + timeoutMs;

    while (Date.now() < deadline) {
      const s = await this.status();

      if (s.status === "succeeded") {
        return { resultUrls: s.resultUrls };
      }
      if (s.status === "errored") {
        throw new MireloError(s.message, s.code, s.httpStatus);
      }

      await sleep(pollIntervalMs);
    }

    throw new MireloError(`Job ${this.jobId} did not complete within the timeout`, "timeout", 408);
  }
}

export interface TextToSfxParams {
  prompt: string;
  durationMs?: number;
  numSamples?: number;
}

export interface VideoToSfxParams {
  durationMs: number;
  startOffsetMs?: number;
  numSamples?: number;
  output?: "audio" | "video";
}

type GenerationInternals =
  | { kind: "text-to-sfx"; params: TextToSfxParams }
  | { kind: "video-to-sfx"; video: Video; params: VideoToSfxParams };

export class GenerationRequest {
  private readonly _basePath: string;
  private readonly _internals: GenerationInternals;
  private readonly _config: HttpConfig;

  constructor(basePath: string, internals: GenerationInternals, config: HttpConfig) {
    this._basePath = basePath;
    this._internals = internals;
    this._config = config;
  }

  private async _buildBody(): Promise<Record<string, unknown>> {
    const body: Record<string, unknown> = {};
    const i = this._internals;

    if (i.kind === "text-to-sfx") {
      body["prompt"] = i.params.prompt;
      if (i.params.durationMs !== undefined) body["duration_ms"] = i.params.durationMs;
      if (i.params.numSamples !== undefined) body["num_samples"] = i.params.numSamples;
    } else if (i.kind === "video-to-sfx") {
      body["video"] = await i.video.resolve(this._config);
      body["duration_ms"] = i.params.durationMs;
      if (i.params.startOffsetMs !== undefined) body["start_offset_ms"] = i.params.startOffsetMs;
      if (i.params.numSamples !== undefined) body["num_samples"] = i.params.numSamples;
      if (i.params.output !== undefined) body["output"] = i.params.output;
    }

    return body;
  }

  private _preflightQuery(): string {
    const params = new URLSearchParams();
    const i = this._internals;
    const durationMs = "params" in i ? i.params.durationMs : undefined;
    const numSamples = "params" in i ? i.params.numSamples : undefined;
    if (durationMs !== undefined) params.set("duration_ms", String(durationMs));
    if (numSamples !== undefined) params.set("num_samples", String(numSamples));
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }

  async preflight(): Promise<PreflightResult> {
    const raw = await httpRequest<{ credits: number; estimated_ms: number }>(
      this._config,
      "GET",
      `${this._config.baseUrl}${this._basePath}/preflight${this._preflightQuery()}`,
    );
    return { credits: raw.credits, estimatedMs: raw.estimated_ms };
  }

  async syncIAcceptHttpTimeoutRisk(): Promise<SyncResult> {
    const body = await this._buildBody();
    const raw = await httpRequest<{ result_urls: string[] }>(
      this._config,
      "POST",
      `${this._config.baseUrl}${this._basePath}/sync`,
      body,
    );
    return { resultUrls: raw.result_urls };
  }

  async submitJob(): Promise<Job> {
    const body = await this._buildBody();
    const raw = await httpRequest<{
      job_id: string;
      job_url: string;
      estimated_ms: number;
      estimated_completion_at: string;
    }>(this._config, "POST", `${this._config.baseUrl}${this._basePath}/jobs`, body);

    return new Job(raw.job_id, raw.estimated_ms, raw.job_url, this._basePath, this._config);
  }
}
