import type {
  TextToSfxParams,
  VideoToSfxParams,
} from "./generation.js";
import { GenerationRequest } from "./generation.js";
import type { HttpConfig } from "./http.js";
import { httpRequest } from "./http.js";
import type { MeResult } from "./types.js";
import { Video } from "./video.js";

export interface MireloClientOptions {
  /** Override the full base URL (e.g. "https://api.mirelo.ai"). Takes precedence over `host`. */
  baseUrl?: string;
  /** Override just the hostname (e.g. "api.mirelo.ai"). Ignored when `baseUrl` is set. */
  host?: string;
  timeoutMs?: number;
  retries?: number;
  backoffMs?: number;
  /** Extra HTTP headers to include on every request (e.g. x-client for plugin identification). */
  extraHeaders?: Record<string, string>;
}

export class MireloClient {
  private readonly _config: HttpConfig;

  constructor(apiKey: string, options: MireloClientOptions = {}) {
    const baseUrl = options.baseUrl ?? `https://${options.host ?? "api.mirelo.ai"}`;
    this._config = {
      apiKey,
      baseUrl,
      timeoutMs: options.timeoutMs ?? 600_000,
      retries: options.retries ?? 0,
      backoffMs: options.backoffMs ?? 1_000,
      extraHeaders: options.extraHeaders,
    };
  }

  async me(): Promise<MeResult> {
    const raw = await httpRequest<{
      id: string;
      email: string;
      credits_available: number;
      overage_enabled: boolean;
    }>(this._config, "GET", `${this._config.baseUrl}/v2/me`);

    return {
      id: raw.id,
      email: raw.email,
      creditsAvailable: raw.credits_available,
      overageEnabled: raw.overage_enabled,
    };
  }

  textToSfx(params: TextToSfxParams): GenerationRequest {
    return new GenerationRequest(
      "/v2/text-to-sfx/v1.5",
      { kind: "text-to-sfx", params },
      this._config,
    );
  }

  videoToSfx(video: Video, params: VideoToSfxParams): GenerationRequest {
    return new GenerationRequest(
      "/v2/video-to-sfx/v1.5",
      { kind: "video-to-sfx", video, params },
      this._config,
    );
  }

}
