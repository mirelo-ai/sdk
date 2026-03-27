import type { HttpConfig } from "./http.js";
import { httpRequest, putBytes } from "./http.js";

export type VideoSource = { type: "url"; video_url: string } | { type: "asset"; asset_id: string };

type VideoInternal =
  | { kind: "url"; url: string }
  | { kind: "bytes"; bytes: Uint8Array; contentType: string }
  | { kind: "asset"; assetId: string };

export class Video {
  private readonly _internal: VideoInternal;
  private _assetId: string | null = null;

  private constructor(internal: VideoInternal) {
    this._internal = internal;
  }

  static fromUrl(url: string): Video {
    return new Video({ kind: "url", url });
  }

  static fromBytes(bytes: Uint8Array, contentType = "video/mp4"): Video {
    return new Video({ kind: "bytes", bytes, contentType });
  }

  /**
   * Create a Video from an already-uploaded asset ID.
   *
   * Use this when you have handled the upload yourself (e.g. to track upload
   * progress or to use streaming) and want to hand the resulting asset to the
   * client for job creation or preflight.
   */
  static fromAssetId(assetId: string): Video {
    return new Video({ kind: "asset", assetId });
  }

  async resolve(config: HttpConfig): Promise<VideoSource> {
    if (this._internal.kind === "url") {
      return { type: "url", video_url: this._internal.url };
    }

    if (this._internal.kind === "asset") {
      return { type: "asset", asset_id: this._internal.assetId };
    }

    if (this._assetId !== null) {
      return { type: "asset", asset_id: this._assetId };
    }

    const { bytes, contentType } = this._internal;

    const { asset_id, upload_url } = await httpRequest<{
      asset_id: string;
      upload_url: string;
    }>(config, "POST", `${config.baseUrl}/v2/assets`, { content_type: contentType });

    await putBytes(upload_url, bytes, contentType, config.timeoutMs);

    this._assetId = asset_id;
    return { type: "asset", asset_id };
  }
}
