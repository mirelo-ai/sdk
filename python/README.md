# mirelo

Official Python SDK for the [Mirelo](https://mirelo.ai) API v2.

Supports both synchronous and async usage via `httpx`.

## Installation

```bash
pip install mirelo
```

## Quick start — sync

```python
from mirelo import MireloClient, Video, MireloError

with MireloClient("sk-your-key") as client:
    # From a public URL — no upload required
    video = Video.from_url("https://example.com/clip.mp4")

    # From raw bytes — e.g. file you read yourself
    # with open("clip.mp4", "rb") as f:
    #     video = Video.from_bytes(f.read(), content_type="video/mp4")

    req = client.video_to_sfx(video, duration_ms=5000)

    try:
        # Check cost first
        cost = req.preflight()
        print(f"{cost.credits} credits, ~{cost.estimated_ms}ms")

        # Submit a background job (recommended)
        job = req.submit_job()

        # Single status check
        status = job.status()
        print(status.status)  # "processing" | "succeeded" | "errored"

        # Or poll until done
        result = job.wait(poll_interval_ms=1000)
        print(result.result_urls)

    except MireloError as e:
        print(f"{e.code} ({e.http_status}): {e.message}")
```

## Quick start — async

```python
import asyncio
from mirelo import AsyncMireloClient, Video, MireloError

async def main():
    async with AsyncMireloClient("sk-your-key") as client:
        video = Video.from_url("https://example.com/clip.mp4")
        req = client.video_to_sfx(video, duration_ms=5000)

        try:
            job = await req.submit_job()
            result = await job.wait()
            print(result.result_urls)
        except MireloError as e:
            print(f"{e.code}: {e.message}")

asyncio.run(main())
```

## Client options

```python
MireloClient(
    "sk-your-key",
    host="api.mirelo.ai",   # default
    timeout_ms=600_000,     # default: 10 minutes, applied to every request
    retries=3,              # default: 0 (disabled); only retries non-4xx errors
    backoff_ms=1_000,       # base for exponential backoff: backoff_ms * 2^attempt
)
```

`AsyncMireloClient` accepts the same options.

## Methods

### `client.me()`

Returns account information including available credits.

```python
me = client.me()
print(me.credits_available, me.overage_enabled)
```

### `client.text_to_sfx(prompt, *, duration_ms, num_samples)`

Generate sound effects from a text prompt.

```python
req = client.text_to_sfx(
    "dramatic thunderclap",
    duration_ms=4_000,   # optional, default 10000
    num_samples=2,       # optional, default 1 (max 4)
)
```

### `client.video_to_sfx(video, *, duration_ms, ...)`

Generate sound effects from a video.

```python
req = client.video_to_sfx(
    video,
    duration_ms=5_000,      # required
    start_offset_ms=1_000,  # optional
    num_samples=1,          # optional
    output="audio",         # optional: "audio" (default) | "video"
)
```

## GenerationRequest

Every generation method returns a `GenerationRequest` with three terminal methods:

### `.preflight()`

Check credit cost and estimated time without consuming credits.

```python
cost = req.preflight()
print(cost.credits, cost.estimated_ms)
```

### `.submit_job()`

Submit a background job and return a `Job` for polling. **This is the recommended approach** — not affected by HTTP proxy timeouts.

```python
job = req.submit_job()
```

### `.sync_i_accept_http_timeout_risk()`

Call the synchronous endpoint, which blocks until generation completes. The deliberately alarming name is intentional: any proxy or load balancer with a timeout shorter than the generation time will cut this off. Use `submit_job()` instead.

```python
result = req.sync_i_accept_http_timeout_risk()
```

## Job / AsyncJob

```python
job = req.submit_job()

# Single status check — returns JobProcessing | JobSucceeded | JobErrored
status = job.status()
if status.status == "processing":
    print(f"{status.progress_percent}% complete")

# Poll until done (raises MireloError if errored or timed out)
result = job.wait(poll_interval_ms=500)  # default 500ms
print(result.result_urls)
```

## Video

```python
# From a public URL — no upload required
video = Video.from_url("https://example.com/clip.mp4")

# From raw bytes — read the file yourself with any API
with open("clip.mp4", "rb") as f:
    video = Video.from_bytes(f.read(), content_type="video/mp4")
```

When `from_bytes` is used, the SDK automatically:

1. Calls `POST /v2/assets` to get a presigned upload URL
2. Uploads the bytes via `PUT`
3. Caches the `asset_id` on the `Video` instance for subsequent reuse

## Error handling

All errors raise `MireloError`:

```python
try:
    result = req.sync_i_accept_http_timeout_risk()
except MireloError as e:
    e.code        # e.g. "insufficient_credits", "invalid_video", "timeout"
    e.http_status # e.g. 402, 422, 408
    e.message     # human-readable description
```
