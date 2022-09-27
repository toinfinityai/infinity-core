from typing import Dict, Optional
from dataclasses import dataclass

from serde import serde


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
