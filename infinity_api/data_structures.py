from enum import Enum, auto
from typing import Dict, Optional
from dataclasses import dataclass

from serde import serde


class HeaderKind(Enum):
    AUTH = auto()
    JSON_CONTENT = auto()
    ACCEPT_JSON = auto()
    ACCEPT_OPENAPI_JSON = auto()
    ACCEPT_OPENAPI_YAML = auto()

    def to_header_dict(self, token: str) -> Dict[str, str]:
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
    PREVIEW = auto()
    STANDARD = auto()


@serde
@dataclass(frozen=True)
class FailedJobRequest:
    status_code: int
    params: Dict


@serde
@dataclass(frozen=True)
class SuccessfulJobRequest:
    job_id: str
    params: Dict


@dataclass(frozen=True)
class CompletedJob:
    job_id: str
    params: Dict
    result_url: Optional[str] = None
