""" Infinity API data structures.

This module contains common or important data structures used in other `infinity-api` modules.
"""

from enum import Enum, auto
from typing import Any, Dict, Optional
from dataclasses import dataclass

from serde import serde


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


@serde
@dataclass(frozen=True)
class FailedJobRequest:
    """A data structure encapsulating a failed API job request.

    Attributes:
        status_code (int): HTTP request status code returned in failure.
        params (:obj:`dict`): Job parameters associated with the failed request.
    """

    status_code: int
    params: Dict[str, Any]


@serde
@dataclass(frozen=True)
class SuccessfulJobRequest:
    """A data structure encapsulating a successful API job request.

    Attributes:
        job_id (str): Unique job ID.
        params (:obj:`dict`): Job parameters associated with the successful request.
    """

    job_id: str
    params: Dict[str, Any]


@dataclass(frozen=True)
class CompletedJob:
    """A data structured encapsulating a completed API job request.

    Attributes:
        job_id (str): Unique job ID.
        params (:obj:`dict`): Job parameters associated with the completed job.
        result_url (str, optional): URL containing completed job result data, if available.
    """

    job_id: str
    params: Dict[str, Any]
    result_url: Optional[str] = None
