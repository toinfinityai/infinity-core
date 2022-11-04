""" Infinity API data structures.

This module contains common or important data structures used in other `infinity-core` modules.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional

JobParams = Dict[str, Any]


class HeaderKind(Enum):
    """Finite set of supported headers for HTTP requests."""

    AUTH = auto()
    JSON_CONTENT = auto()
    ACCEPT_JSON = auto()
    ACCEPT_OPENAPI_JSON = auto()
    ACCEPT_OPENAPI_YAML = auto()

    def to_header_dict(self, token: str) -> Dict[str, str]:
        """Convert header variant to header dictionary.

        Returns:
            Dict containing an HTTP request key-value pair.
        """
        if self == HeaderKind.AUTH:
            return {"Authorization": f"Token {token}"}
        elif self == HeaderKind.JSON_CONTENT:
            return {"Content-Type": "application/json"}
        elif self == HeaderKind.ACCEPT_JSON:
            return {"Accept": "application/json"}
        elif self == HeaderKind.ACCEPT_OPENAPI_JSON:
            return {"Accept": "application/vnd.oai.openapi+json"}
        elif self == HeaderKind.ACCEPT_OPENAPI_YAML:
            return {"Accept": "application/vnd.oai.openapi"}
        else:
            raise ValueError(f"Unsupported header kind {self}")


class JobType(Enum):
    """Fundamental job type supported by the Infinity API."""

    PREVIEW = auto()
    STANDARD = auto()


@dataclass(frozen=True)
class CompletedJob:
    """A data structured encapsulating a completed API job request.

    Args:
        uid: Unique job ID.
        generator: Name of the generator for the job.
        params: Job parameters associated with the completed job.
        result_url: URL containing completed job result data, if available.
    """

    uid: str
    generator: str
    params: JobParams
    result_url: Optional[str] = None

    def try_into_valid_completed_job(self) -> Optional["ValidCompletedJob"]:
        if self.result_url is not None:
            return ValidCompletedJob(
                uid=self.uid,
                generator=self.generator,
                params=self.params,
                result_url=self.result_url,
            )
        else:
            return None


@dataclass(frozen=True)
class ValidCompletedJob:
    """A data structured encapsulating a valid completed API job request.

    Args:
        uid: Unique job ID.
        generator: Name of the generator for the job.
        params: Job parameters associated with the completed job.
        result_url: URL containing completed job result data.
    """

    uid: str
    generator: str
    params: JobParams
    result_url: str

    @classmethod
    def try_from_completed_job(cls, completed_job: CompletedJob) -> Optional["ValidCompletedJob"]:
        if completed_job.result_url is not None:
            return cls(
                uid=completed_job.uid,
                generator=completed_job.generator,
                params=completed_job.params,
                result_url=completed_job.result_url,
            )
        else:
            return None