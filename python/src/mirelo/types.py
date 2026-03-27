from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

class MireloError(Exception):
    """Raised on any API or network error."""

    def __init__(self, message: str, code: str, http_status: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status

    def __repr__(self) -> str:
        return (
            f"MireloError(code={self.code!r}, "
            f"http_status={self.http_status}, "
            f"message={self.message!r})"
        )

@dataclass
class MeResult:
    id: str
    email: str
    credits_available: float
    overage_enabled: bool

@dataclass
class PreflightResult:
    credits: float
    estimated_ms: int

@dataclass
class SyncResult:
    result_urls: list[str]

@dataclass
class JobProcessing:
    status: Literal["processing"]
    progress_percent: int
    estimated_completion_at: str

@dataclass
class JobSucceeded:
    status: Literal["succeeded"]
    result_urls: list[str]

@dataclass
class JobErrored:
    status: Literal["errored"]
    code: str
    http_status: int
    message: str

JobStatus = Union[JobProcessing, JobSucceeded, JobErrored]
