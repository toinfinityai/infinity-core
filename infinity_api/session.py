""" Infinity AI Session API for synthetic data generation.

This module provides a Session-style API to wrap interaction with the Infinity AI REST API. The
Session API abstracts away details of user authentication and certain configuration for all
activities after a session is initialized.
"""

import functools
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    _generator_param_info: List[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._generator_param_info = api.get_single_generator_data(
            token=self.token, generator_name=self.generator, server=self.server
        ).json()["params"]

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
    def generator_parameters(self) -> Dict[str, Dict[str, Any]]:
        """dict: Parameters of the generator with metadata."""
        pdict = dict()
        for p in self._generator_param_info:
            pdict[p["name"]] = {"type": p["type"], "default_value": p["default_value"], "options": p["options"]}

        return pdict

    def _submit_batch(
        self, job_params: List[Dict[str, Any]], job_type: JobType, batch_folder_suffix: Optional[str] = None
    ) -> Tuple[ba.Batch, Optional[Path]]:
        batch, batch_path = ba.submit_batch_to_api(
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
        return batch, batch_path

    def submit_preview_batch(
        self, job_params: List[Dict[str, Any]], batch_folder_suffix: Optional[str] = None
    ) -> Tuple[ba.Batch, Optional[Path]]:
        """Submit a batch of 1 or more previews to the Infinity API.

        Args:
            job_params: A :obj:`list` of :obj:`dict` containing job parameters for the batch.
            batch_folder_suffix: Optional descriptive suffix for batch folder stored on disk.

        Returns:
            Tuple of the created :obj:`Batch` instance and a path to its metadata on disk.
        """
        return self._submit_batch(
            job_params=job_params, job_type=JobType.PREVIEW, batch_folder_suffix=batch_folder_suffix
        )

    def submit_standard_batch(
        self, job_params: List[Dict[str, Any]], batch_folder_suffix: Optional[str] = None
    ) -> Tuple[ba.Batch, Optional[Path]]:
        """Submit a batch of 1 or more standard jobs (e.g., videos) to the Infinity API.

        Args:
            job_params: A :obj:`list` of :obj:`dict` containing job parameters for the batch.
            batch_folder_suffix: Optional descriptive suffix for batch folder stored on disk.

        Returns:
            Tuple of the created :obj:`Batch` instance and a path to its metadata on disk.
        """
        return self._submit_batch(
            job_params=job_params, job_type=JobType.STANDARD, batch_folder_suffix=batch_folder_suffix
        )

    def query_usage_last_n_days(self, n_days: int) -> Dict[str, Any]:
        """Query API for usage stats over the last N days.

        Args:
            n_days: Number of days looking back to gather usage stats for.

        Returns:
            Dictionary containing usage stats by generator.

        Raises:
            HTTPError: When the API query returns with an error status code.
        """
        r = api.get_usage_last_n_days(token=self.token, n_days=n_days, server=self.server)
        r.raise_for_status()
        return dict(r.json())

    def save(self) -> Path:
        """Save the :obj:`Session` to disk.

        Returns:
            The path on disk where the `Session` was saved.
        """
        serialized_session_file = Path(self.output_dir) / f"{self.session_filename}"
        serialized_session_file.mkdir(parents=True, exist_ok=True)
        with open(serialized_session_file, "w") as f:
            f.write(self.to_json())

        return serialized_session_file
