import { MireloError } from "./types.js";

export interface HttpConfig {
  apiKey: string;
  baseUrl: string;
  timeoutMs: number;
  retries: number;
  backoffMs: number;
  extraHeaders?: Record<string, string>;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function parseErrorResponse(response: Response): Promise<MireloError> {
  let code = "server_error";
  let message = response.statusText;
  try {
    const data = (await response.json()) as Record<string, unknown>;
    const err = data["error"] as Record<string, unknown> | undefined;
    code = (err?.["code"] as string | undefined) ?? code;
    message = (err?.["message"] as string | undefined) ?? message;
  } catch {
    // ignore JSON parse failure
  }
  return new MireloError(message, code, response.status);
}

function classifyCaughtError(e: unknown): MireloError | null {
  if (e instanceof DOMException && e.name === "AbortError") {
    return new MireloError("Request timed out", "timeout", 408);
  }
  if (e instanceof TypeError) {
    return new MireloError(e instanceof Error ? e.message : "Network error", "network_error", 0);
  }
  return null;
}

export async function httpRequest<T>(
  config: HttpConfig,
  method: string,
  url: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${config.apiKey}`,
    ...config.extraHeaders,
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let lastError: MireloError = new MireloError("Request failed", "server_error", 500);

  for (let attempt = 0; attempt <= config.retries; attempt++) {
    if (attempt > 0) {
      await sleep(config.backoffMs * Math.pow(2, attempt - 1));
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeoutMs);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const err = await parseErrorResponse(response);
        // never retry 4xx — caller made a bad request
        if (response.status >= 400 && response.status < 500) throw err;
        lastError = err;
        continue;
      }

      return (await response.json()) as T;
    } catch (e) {
      clearTimeout(timeoutId);
      if (e instanceof MireloError) throw e;

      const classified = classifyCaughtError(e);
      if (classified !== null) {
        lastError = classified;
        continue;
      }

      throw e;
    }
  }

  throw lastError;
}

export async function putBytes(
  url: string,
  bytes: Uint8Array,
  contentType: string,
  timeoutMs: number,
): Promise<void> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": contentType },
      // Cast needed: TypeScript's Uint8Array<ArrayBufferLike> doesn't satisfy
      // BlobPart when the buffer might be a SharedArrayBuffer, but at runtime
      // this is always safe since Video.fromBytes only accepts plain Uint8Arrays.
      body: new Blob([bytes as unknown as ArrayBuffer], { type: contentType }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new MireloError(
        `Upload failed: ${response.statusText}`,
        "upload_failed",
        response.status,
      );
    }
  } catch (e) {
    clearTimeout(timeoutId);
    if (e instanceof MireloError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new MireloError("Upload timed out", "timeout", 408);
    }
    throw new MireloError(e instanceof Error ? e.message : "Upload failed", "upload_failed", 0);
  }
}
