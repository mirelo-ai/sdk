# Mirelo SDK

Official SDKs for the [Mirelo](https://mirelo.ai) API — generate sound effects from text or video using AI.

Get an API key at [mirelo.ai](https://mirelo.ai).

## Packages

| Package | Install | Docs |
|---------|---------|------|
| Node.js / TypeScript | `npm install @mirelo/sdk` | [node/](node/) |
| Python | `pip install mirelo-sdk` | [python/](python/) |

## Quick start — Node.js

```typescript
import { MireloClient, Video, MireloError } from "@mirelo/sdk";

const client = new MireloClient("sk-your-key");

// Generate sound effects from a video URL
const video = Video.fromUrl("https://example.com/clip.mp4");
const req = client.videoToSfx(video, { durationMs: 5000 });

try {
  const cost = await req.preflight();
  console.log(`${cost.credits} credits, ~${cost.estimatedMs}ms`);

  const job = await req.submitJob();
  const result = await job.wait();
  console.log(result.resultUrls);
} catch (e) {
  if (e instanceof MireloError) {
    console.error(`${e.code} (${e.httpStatus}): ${e.message}`);
  }
}
```

## Quick start — Python

```python
from mirelo import MireloClient, Video, MireloError

with MireloClient("sk-your-key") as client:
    video = Video.from_url("https://example.com/clip.mp4")
    req = client.video_to_sfx(video, duration_ms=5000)

    try:
        job = req.submit_job()
        result = job.wait()
        print(result.result_urls)
    except MireloError as e:
        print(f"{e.code} ({e.http_status}): {e.message}")
```

## Features

- **Text to sound effects** — describe a sound, get audio
- **Video to sound effects** — generate sounds that match what's on screen
- Sync and async (job-based) generation modes
- Preflight check to estimate credits and time before generating
- Retry logic with exponential backoff
- Works in Node.js, browsers, Deno, Bun, and Adobe UXP (Node SDK)
- Sync and async Python clients via `httpx`

## Documentation

- Full Node.js SDK docs: [node/README.md](node/README.md)
- Full Python SDK docs: [python/README.md](python/README.md)
- OpenAPI spec: [openapi.yaml](openapi.yaml)
- API reference: [mirelo.ai/docs](https://mirelo.ai/docs)

## License

MIT — [Mirelo AI GmbH](https://mirelo.ai)
