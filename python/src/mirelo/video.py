from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

class Video:
    """
    Represents a video source for generation requests.

    Create with ``Video.from_url()`` or ``Video.from_bytes()``.
    The asset upload (when using bytes) is performed lazily the first time
    this video is used in a generation call and the ``asset_id`` is cached
    for subsequent reuse.
    """

    def __init__(
        self,
        *,
        url: str | None = None,
        data: bytes | None = None,
        content_type: str = "video/mp4",
    ) -> None:
        self._url = url
        self._data = data
        self._content_type = content_type
        self._asset_id: str | None = None

    @classmethod
    def from_url(cls, url: str) -> Video:
        """Create a video from a publicly accessible URL. No upload is performed."""
        return cls(url=url)

    @classmethod
    def from_bytes(cls, data: bytes, content_type: str = "video/mp4") -> Video:
        """
        Create a video from raw bytes.

        The bytes are uploaded to Mirelo storage the first time this video is
        used in a generation call. Subsequent calls reuse the cached asset ID.
        """
        return cls(data=data, content_type=content_type)

    # ------------------------------------------------------------------
    # Internal resolution helpers
    # ------------------------------------------------------------------

    def _resolve_url_source(self) -> dict[str, str]:
        assert self._url is not None
        return {"type": "url", "video_url": self._url}

    def resolve_sync(
        self,
        client: httpx.Client,
        base_url: str,
        headers: dict[str, str],
        timeout_ms: int,
        retries: int = 0,
        backoff_ms: int = 1_000,
    ) -> dict[str, str]:
        if self._url is not None:
            return self._resolve_url_source()

        if self._asset_id is not None:
            return {"type": "asset", "asset_id": self._asset_id}

        from . import http as _http

        result = _http.request(
            client,
            "POST",
            f"{base_url}/v2/assets",
            headers=headers,
            json={"content_type": self._content_type},
            retries=retries,
            backoff_ms=backoff_ms,
        )
        asset_id: str = result["asset_id"]
        upload_url: str = result["upload_url"]

        assert self._data is not None
        _http.put_bytes(upload_url, self._data, self._content_type, timeout_ms)

        self._asset_id = asset_id
        return {"type": "asset", "asset_id": asset_id}

    async def resolve_async(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        headers: dict[str, str],
        timeout_ms: int,
        retries: int = 0,
        backoff_ms: int = 1_000,
    ) -> dict[str, str]:
        if self._url is not None:
            return self._resolve_url_source()

        if self._asset_id is not None:
            return {"type": "asset", "asset_id": self._asset_id}

        from . import async_http as _ahttp

        result = await _ahttp.request(
            client,
            "POST",
            f"{base_url}/v2/assets",
            headers=headers,
            json={"content_type": self._content_type},
            retries=retries,
            backoff_ms=backoff_ms,
        )
        asset_id: str = result["asset_id"]
        upload_url: str = result["upload_url"]

        assert self._data is not None
        await _ahttp.put_bytes(upload_url, self._data, self._content_type, timeout_ms)

        self._asset_id = asset_id
        return {"type": "asset", "asset_id": asset_id}
