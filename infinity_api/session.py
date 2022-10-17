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


class GeneratorParameterException(Exception):
    pass


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

    def _validate_params(self, user_params: Dict[str, Any]) -> None:
        pinfo = self.gen_param_info
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

        raise GeneratorParameterException(error_string)

    @functools.cached_property
    def gen_param_info(self) -> Dict[str, Dict[str, Any]]:
        """dict: Parameters of the generator with metadata."""
        pdict = dict()
        for p in self._generator_param_info:
            pdict[p["name"]] = {"type": p["type"], "default_value": p["default_value"], "options": p["options"]}

        return pdict

    @functools.cached_property
    def gen_default_values(self) -> Dict[str, Any]:
        """dict: Default values for parameters of the generator."""
        # TODO: Don't special case `state`: fix in backend/compute if default value is encountered.
        return {k: d["default_value"] for k, d in self.gen_param_info.items() if not k == "state"}

    @functools.cached_property
    def gen_param_types(self) -> Dict[str, str]:
        """dict: Types for parameters of the generator."""
        return {k: d["type"] for k, d in self.gen_param_info.items()}

    @functools.cached_property
    def gen_param_options(self) -> Dict[str, Any]:
        """dict: Options and metadata for parameters of the generator."""
        return {k: d["options"] for k, d in self.gen_param_info.items()}

    def submit_to_api(
        self, job_params: List[Dict[str, Any]], preview: bool = True, batch_name: Optional[str] = None
    ) -> ba.Batch:
        """Submit a batch of 1 or more synthetic data batch jobs to the Infinity API.

        Args:
            job_params: A :obj:`list` of :obj:`dict` containing job parameters for the batch.
            preview: Flag to indicate a preview is desired instead of a full job (e.g., video).
            description: Optional descriptive for the submission.

        Returns:
            The created :obj:`Batch` instance.

        Raises:
            GeneratorParameterException: If supplied parameters are not supported by the generator.
        """
        complete_params = []
        for jp in job_params:
            # TODO: Or do we just fully want to defer to the backend's validation?
            self._validate_params(jp)
            complete_params.append({**self.gen_default_values, **jp})

        # TODO: We can easily check from the API info if `preview` is supported by the generator.
        job_type = JobType.PREVIEW if preview else JobType.STANDARD
        batch, _ = ba.submit_batch_to_api(
            token=self.token,
            generator=self.generator,
            job_type=job_type,
            job_params=complete_params,
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
