"""
Mirelo API SDK — Python client.

Sync usage::

    from mirelo import MireloClient, Video, MireloError

    with MireloClient("sk-...") as client:
        video = Video.from_url("https://example.com/clip.mp4")
        job = client.video_to_sfx(video, duration_ms=5000).submit_job()
        result = job.wait()
        print(result.result_urls)

Async usage::

    from mirelo import AsyncMireloClient, Video, MireloError

    async with AsyncMireloClient("sk-...") as client:
        video = Video.from_bytes(data, content_type="video/mp4")
        job = await client.video_to_sfx(video, duration_ms=5000).submit_job()
        result = await job.wait()
        print(result.result_urls)
"""

from .async_client import AsyncMireloClient
from .async_generation import AsyncGenerationRequest, AsyncJob
from .client import MireloClient
from .generation import (
    GenerationRequest,
    Job,
    TextToSfxParams,
    VideoToSfxParams,
)
from .types import (
    JobErrored,
    JobProcessing,
    JobStatus,
    JobSucceeded,
    MeResult,
    MireloError,
    PreflightResult,
    SyncResult,
)
from .video import Video

__all__ = [
    "MireloClient",
    "AsyncMireloClient",
    "Video",
    "MireloError",
    "GenerationRequest",
    "AsyncGenerationRequest",
    "Job",
    "AsyncJob",
    "TextToSfxParams",
    "VideoToSfxParams",
    "MeResult",
    "PreflightResult",
    "SyncResult",
    "JobStatus",
    "JobProcessing",
    "JobSucceeded",
    "JobErrored",
]
