""" Infinity AI Session API for synthetic data generation.

This module provides a Session-style API to wrap interaction with the Infinity AI REST API. The
Session API abstracts away details of user authentication and certain configuration for all
activities after a session is initialized.
"""

import functools
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from serde import deserialize, field, serialize
from serde.json import from_json, to_json

import infinity_api.api as api
import infinity_api.batch as ba
from infinity_api.data_structures import JobType


@serialize
@deserialize
@dataclass(frozen=False)
class Session:
    """An encapsulation of a user session to interact with the Infinity API."""

    name: str
    generator: str
    output_dir: str = "tmp"
    server: str = api.DEFAULT_SERVER
    description: Optional[str] = None
    batches: List[ba.Batch] = field(default_factory=list)
    token: str = field(default="", metadata={"serde_skip": True})

    @property
    def session_filename(self) -> str:
        """str: Fully constructed session output filename"""
        return f"{self.name}_session.json"

    def to_json(self) -> str:
        """Serialize the session to a JSON string.

        Returns:
            JSON string containing serialized batch data.
        """
        return to_json(self, indent=4)

    @classmethod
    def from_json(cls, json_str: str, token: str) -> "Session":
        """Deserialize a JSON string into a :obj:`Session`.

        Args:
            json_str: JSON string containing a previously serialized batch's information.
            token: API authentication token associated with the batch.

        Returns:
            The deserialized :obj:`Session`.
        """
        deserialized_sesh = from_json(cls, json_str)
        return replace(deserialized_sesh, token=token)

    @functools.cached_property
    def parameters(self) -> Dict[str, str]:
        # TODO: Get generator paramters from API call.
        raise NotImplementedError

    def _submit_batch(
        self, job_params: List[Dict[str, Any]], job_type: JobType, batch_folder_suffix: Optional[str] = None
    ) -> ba.Batch:
        batch, _ = ba.submit_batch_to_api(
            token=self.token,
            generator=self.generator,
            job_type=job_type,
            job_params=job_params,
            output_dir=self.output_dir,
            batch_folder_suffix=batch_folder_suffix,
            server=self.server,
            write_to_file=True,
        )
        self.batches.append(batch)
        return batch

    def submit_preview_batch(
        self, job_params: List[Dict[str, Any]], batch_folder_suffix: Optional[str] = None
    ) -> ba.Batch:
        return self._submit_batch(
            job_params=job_params, job_type=JobType.PREVIEW, batch_folder_suffix=batch_folder_suffix
        )

    def submit_standard_batch(
        self, job_params: List[Dict[str, Any]], batch_folder_suffix: Optional[str] = None
    ) -> ba.Batch:
        return self._submit_batch(
            job_params=job_params, job_type=JobType.STANDARD, batch_folder_suffix=batch_folder_suffix
        )

    def write_to_file(self) -> Path:
        serialized_session_file = Path(self.output_dir) / f"{self.session_filename}"
        serialized_session_file.mkdir(parents=True, exist_ok=True)
        with open(serialized_session_file, "w") as f:
            f.write(self.to_json())

        return serialized_session_file
