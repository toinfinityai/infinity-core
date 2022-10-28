""" Infinity AI Session API for synthetic data generation.

This module provides a Session-style API to wrap interaction with the Infinity AI REST API. The
Session API abstracts away details of user authentication and certain configuration for all
activities after a session is initialized.
"""

import datetime
import functools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import infinity_api.api as api
from infinity_api.batch import Batch, submit_batch
from infinity_api.data_structures import JobParams, JobType


class ParameterValidationError(Exception):
    pass


@dataclass(frozen=False)
class Session:
    """An encapsulation of a user session to interact with the Infinity API."""

    token: str
    name: str
    generator: str
    server: str = api.DEFAULT_SERVER
    batches: List[Batch] = field(default_factory=list)
    _generator_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._generator_info = api.get_single_generator_data(
            token=self.token, generator_name=self.generator, server=self.server
        ).json()

    def _validate_params(self, user_params: JobParams) -> None:
        pinfo = self.parameter_info
        valid_parameter_set = set(pinfo.keys())
        unsupported_parameter_set = set()
        constraint_violation_list = list()
        for uk, uv in user_params.items():
            if uk not in valid_parameter_set:
                unsupported_parameter_set.add(uk)
                continue
            param_options = pinfo[uk]["options"]
            if "min" in param_options:
                cv = param_options["min"]
                if uv < cv:
                    constraint_violation_list.append((uk, "min", cv, uv))
            if "max" in param_options:
                cv = param_options["max"]
                if uv > cv:
                    constraint_violation_list.append((uk, "max", cv, uv))
            if "choices" in param_options:
                cv = param_options["choices"]
                if uv not in cv:
                    constraint_violation_list.append((uk, "choices", cv, uv))

        had_unsupported_parameter = False if unsupported_parameter_set == set() else True
        violated_constraints = False if len(constraint_violation_list) == 0 else True

        if not had_unsupported_parameter and not violated_constraints:
            return
        else:
            error_string = ""
            if had_unsupported_parameter:
                error_string += "\n\nUnsupported parameters:\n"
                for p in unsupported_parameter_set:
                    error_string += f"`{p}`"
            if violated_constraints:
                error_string += "\n\nConstraint violations:\n"
                for p, c, cv, pv in constraint_violation_list:
                    error_string += f"Input parameter `{p}` violated constraint `{c}` ({cv}) with value {pv}\n"

        raise ParameterValidationError(error_string)

    @functools.cached_property
    def parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """dict: Parameters of the generator with metadata."""
        pdict = dict()
        for p in self._generator_info["params"]:
            pdict[p["name"]] = {"type": p["type"], "default_value": p["default_value"], "options": p["options"]}

        return pdict

    @functools.cached_property
    def default_job(self) -> JobParams:
        """dict: Default values for parameters of the generator."""
        return {k: d["default_value"] for k, d in self.parameter_info.items()}

    def submit(self, job_params: List[JobParams], is_preview: bool = True, batch_name: Optional[str] = None) -> Batch:
        """Submit a batch of 1 or more synthetic data batch jobs to the Infinity API.

        Args:
            job_params: A :obj:`list` of :obj:`dict` containing job parameters for the batch.
            is_preview: Flag to indicate a preview is desired instead of a full job (e.g., video).
            description: Optional descriptive for the submission.

        Returns:
            The created :obj:`Batch` instance.

        Raises:
            ParameterValidationError: If supplied parameters are not supported by the generator.
        """
        complete_params = []
        for jp in job_params:
            # TODO: Or do we just fully want to defer to the backend's validation?
            self._validate_params(jp)
            complete_params.append({**self.default_job, **jp})

        # TODO: We can easily check from the API info if `preview` is supported by the generator.
        job_type = JobType.PREVIEW if is_preview else JobType.STANDARD
        batch = submit_batch(
            token=self.token,
            generator=self.generator,
            job_type=job_type,
            job_params=complete_params,
            name=batch_name,
            server=self.server,
        )
        self.batches.append(batch)
        return batch

    # def rerun_batch(
    #     self, batch: ba.Batch, overrides: JobParams, preview: bool = True, batch_name: Optional[str] = None
    # ) -> ba.Batch:
    #     # TODO: Will this work for SenseFit et alia in addition to VisionFit?
    #     # TODO: If not, let's standardize how `state` is expressed so that this will work
    #     # TODO: automatically for all generators and their jobs.
    #     self._validate_params(overrides)
    #     job_params = []
    #     for j in batch.jobs:
    #         params = j.params
    #         if "state" in self.parameter_info.keys():
    #             params["state"] = j.uid
    #         # TODO: Confirm this does the right override order of operations.
    #         params = {**self.default_job, **params, **overrides}
    #         job_params.append(params)

    #     return self.submit(job_params=job_params, preview=preview, batch_name=batch_name)

    def batch_from_api(self, batch_id: str) -> Batch:
        return Batch.from_api(token=self.token, batch_id=batch_id, server=self.server)

    def get_batches_last_n_days(self, n_days: int) -> List[Dict[str, Any]]:
        end_time = datetime.datetime.now().astimezone()
        start_time = end_time - datetime.timedelta(days=n_days)
        r = api.get_batch_list(token=self.token, start_time=start_time, end_time=end_time, server=self.server)
        r.raise_for_status()
        data: List[Dict[str, Any]] = r.json()
        for batch in data:
            batch["created"] = datetime.datetime.fromisoformat(batch["created"])

        return data

    def get_usage_stats_last_n_days(self, n_days: int) -> Dict[str, Any]:
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
