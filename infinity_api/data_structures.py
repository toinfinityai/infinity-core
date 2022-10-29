""" Infinity API data structures.

This module contains common or important data structures used in other `infinity-api` modules.
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

    Attributes:
        uid (str): Unique job ID.
        generator (str): Name of the generator for the job.
        params (:obj:`dict`): Job parameters associated with the completed job.
        result_url (str, optional): URL containing completed job result data, if available.
    """

    uid: str
    generator: str
    params: JobParams
    result_url: Optional[str] = None


@dataclass(frozen=True)
class ValidCompletedJob:
    """A data structured encapsulating a valid completed API job request.

    Attributes:
        uid (str): Unique job ID.
        generator (str): Name of the generator for the job.
        params (:obj:`dict`): Job parameters associated with the completed job.
        result_url (str): URL containing completed job result data.
    """

    uid: str
    generator: str
    params: JobParams
    result_url: str
