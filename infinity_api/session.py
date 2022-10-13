""" Infinity AI Session API for synthetic data generation.

This module provides a Session-style API to wrap interaction with the Infinity AI REST API. The
Session API abstracts away details of user authentication and certain configuration for all
activities after a session is initialized.
"""

import functools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import infinity_api.api as api
import infinity_api.batch as ba
from infinity_api.data_structures import JobType


@dataclass(frozen=False)
class Session:
    """An encapsulation of a user session to interact with the Infinity API."""

    token: str
    name: str
    generator: str
    server: str = api.DEFAULT_SERVER
    batches: List[ba.Batch] = field(default_factory=list)
    _generator_param_info: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._generator_param_info = api.get_single_generator_data(
            token=self.token, generator_name=self.generator, server=self.server
        ).json()["params"]

    @functools.cached_property
    def gen_param_info(self) -> Dict[str, Dict[str, Any]]:
        """dict: Parameters of the generator with metadata."""
        pdict = dict()
        for p in self._generator_param_info:
            pdict[p["name"]] = {"type": p["type"], "default_value": p["default_value"], "options": p["options"]}

        return pdict

    @functools.cached_property
    def gen_default_values(self) -> Dict[str, Any]:
        return {k: d["default_value"] for k, d in self.gen_param_info.items()}

    @functools.cached_property
    def gen_param_types(self) -> Dict[str, str]:
        return {k: d["type"] for k, d in self.gen_param_info.items()}

    @functools.cached_property
    def gen_param_options(self) -> Dict[str, Any]:
        return {k: d["options"] for k, d in self.gen_param_info.items()}

    def submit_to_api(
        self, job_params: List[Dict[str, Any]], job_type: JobType = JobType.PREVIEW, batch_name: Optional[str] = None
    ) -> ba.Batch:
        """Submit a batch of 1 or more previews to the Infinity API.

        Args:
            job_params: A :obj:`list` of :obj:`dict` containing job parameters for the batch.
            job_type: Type of job desired (e.g., preview or video).
            description: Optional descriptive for the submission.

        Returns:
            The created :obj:`Batch` instance.
        """
        batch, _ = ba.submit_batch_to_api(
            token=self.token,
            generator=self.generator,
            job_type=job_type,
            job_params=job_params,
            batch_folder_suffix=batch_name,
            server=self.server,
            write_to_file=True,
        )
        self.batches.append(batch)
        return batch

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
