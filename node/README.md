# mirelo

Official JavaScript/TypeScript SDK for the [Mirelo](https://mirelo.ai) API v2.

Works in any environment that supports `fetch` and `Uint8Array`: Node.js, browsers, Adobe UXP, Deno, Bun, and more — no Node.js-specific APIs are used.

## Installation

```bash
npm install @mirelo/sdk
# or
bun add @mirelo/sdk
```

## Quick start

```typescript
import { MireloClient, Video, MireloError } from "@mirelo/sdk";

const client = new MireloClient("sk-your-key");

// From a URL — no upload needed
const video = Video.fromUrl("https://example.com/clip.mp4");

// From bytes — works in every environment
// const video = Video.fromBytes(uint8ArrayData, "video/mp4");

const req = client.videoToSfx(video, { durationMs: 5000 });

try {
  // Check cost before generating
  const cost = await req.preflight();
  console.log(`${cost.credits} credits, ~${cost.estimatedMs}ms`);

  // Submit a job (recommended — avoids HTTP timeout risk)
  const job = await req.submitJob();

  // Check status once
  const status = await job.status();
  console.log(status.status); // "processing" | "succeeded" | "errored"

  // Or wait until done
  const result = await job.wait({ pollIntervalMs: 1000 });
  console.log(result.resultUrls);
} catch (e) {
  if (e instanceof MireloError) {
    console.error(`${e.code} (${e.httpStatus}): ${e.message}`);
  }
}
```

## Client options

```typescript
const client = new MireloClient("sk-your-key", {
  host: "api.mirelo.ai", // default
  timeoutMs: 600_000, // default: 10 minutes, applied to every request
  retries: 3, // default: 0 (disabled); only retries non-4xx errors
  backoffMs: 1_000, // base for exponential backoff: backoffMs * 2^attempt
});
```

## Methods

### `client.me()`

Returns account info including available credits.

```typescript
const me = await client.me();
console.log(me.creditsAvailable, me.overageEnabled);
```

### `client.textToSfx(params)`

Generate sound effects from a text prompt.

```typescript
const req = client.textToSfx({
  prompt: "dramatic thunderclap",
  durationMs: 4000, // optional, default 10000
  numSamples: 2, // optional, default 1 (max 4)
});
```

### `client.videoToSfx(video, params)`

Generate sound effects from a video.

```typescript
const req = client.videoToSfx(video, {
  durationMs: 5000, // required
  startOffsetMs: 1000, // optional
  numSamples: 1, // optional
  output: "audio", // optional: "audio" (default) | "video"
});
```

## GenerationRequest

Every generation method returns a `GenerationRequest` with three terminal methods:

### `.preflight()`

Check the credit cost and estimated time without generating anything.

```typescript
const { credits, estimatedMs } = await req.preflight();
```

### `.submitJob()`

Submit a background job and return a `Job` object. **This is the recommended approach** — it is not affected by HTTP proxy timeouts.

```typescript
const job = await req.submitJob();
```

### `.syncIAcceptHttpTimeoutRisk()`

Call the synchronous endpoint, which blocks until generation completes. The deliberately alarming name is intentional: any proxy or load balancer with a timeout shorter than the generation time will cut this request off. Use `submitJob()` instead for production.

```typescript
const result = await req.syncIAcceptHttpTimeoutRisk();
```

## Job

```typescript
const job = await req.submitJob();

// Single status check
const status = await job.status();
if (status.status === "processing") {
  console.log(`${status.progressPercent}% done`);
}

// Poll until complete (throws MireloError if errored or timed out)
const result = await job.wait({ pollIntervalMs: 500 }); // default 500ms
console.log(result.resultUrls);
```

## Video

```typescript
// From a public URL — no upload required
const video = Video.fromUrl("https://example.com/clip.mp4");

// From raw bytes — works everywhere (Node.js, browsers, UXP, etc.)
// Node.js Buffer extends Uint8Array and works here directly.
const video = Video.fromBytes(bytes, "video/mp4");
```

When `fromBytes` is used, the SDK automatically:

1. Calls `POST /v2/assets` to get a presigned upload URL
2. Uploads the bytes via `PUT`
3. Caches the resulting `asset_id` on the `Video` instance for subsequent calls

## Error handling

All errors throw `MireloError`:

```typescript
try {
  const result = await req.syncIAcceptHttpTimeoutRisk();
} catch (e) {
  if (e instanceof MireloError) {
    e.code; // e.g. "insufficient_credits", "invalid_video", "timeout"
    e.httpStatus; // e.g. 402, 422, 408
    e.message; // human-readable description
  }
}
```
