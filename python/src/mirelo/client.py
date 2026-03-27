from __future__ import annotations

from types import TracebackType

import httpx

from . import http as _http
from .generation import (
    GenerationRequest,
    TextToSfxParams,
    VideoToSfxParams,
)
from typing import Literal

from .types import MeResult
from .video import Video

class MireloClient:
    """
    Synchronous Mirelo API client.

    Use as a context manager to ensure the underlying HTTP connection is closed::

        with MireloClient("sk-...") as client:
            result = client.text_to_sfx("thunder").submit_job().wait()
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        host: str = "api.mirelo.ai",
        timeout_ms: int = 600_000,
        retries: int = 0,
        backoff_ms: int = 1_000,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url if base_url is not None else f"https://{host}"
        self._timeout_ms = timeout_ms
        self._retries = retries
        self._backoff_ms = backoff_ms
        self._headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
        if extra_headers:
            self._headers.update(extra_headers)
        self._client = httpx.Client(timeout=timeout_ms / 1_000)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MireloClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def me(self) -> MeResult:
        """Return account information including available credits."""
        raw = _http.request(
            self._client,
            "GET",
            f"{self._base_url}/v2/me",
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return MeResult(
            id=raw["id"],
            email=raw["email"],
            credits_available=raw["credits_available"],
            overage_enabled=raw["overage_enabled"],
        )

    def text_to_sfx(
        self,
        prompt: str,
        *,
        duration_ms: int = 10_000,
        num_samples: int = 1,
    ) -> GenerationRequest:
        return GenerationRequest(
            base_path="/v2/text-to-sfx/v1.5",
            params=TextToSfxParams(prompt=prompt, duration_ms=duration_ms, num_samples=num_samples),
            client=self._client,
            base_url=self._base_url,
            headers=self._headers,
            timeout_ms=self._timeout_ms,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )

    def video_to_sfx(
        self,
        video: Video,
        *,
        duration_ms: int,
        start_offset_ms: int = 0,
        num_samples: int = 1,
        output: Literal["audio", "video"] = "audio",
    ) -> GenerationRequest:
        return GenerationRequest(
            base_path="/v2/video-to-sfx/v1.5",
            params=VideoToSfxParams(
                duration_ms=duration_ms,
                start_offset_ms=start_offset_ms,
                num_samples=num_samples,
                output=output,
            ),
            client=self._client,
            base_url=self._base_url,
            headers=self._headers,
            video=video,
            timeout_ms=self._timeout_ms,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
