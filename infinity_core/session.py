""" Infinity AI Session API for synthetic data generation.

This module provides a Session-style API to wrap interaction with the Infinity AI REST API. The
Session API abstracts away details of user authentication and enables ergonomics in areas such as
parameter validation and job parameter construction once a session is initialized.

Synthetic data generation requests (via `Session.submit`) return a `Batch` instance (detailed in
the `batch` module) which provides many facilities such as querying status of the batch, awaiting
full completion, and downloading ready results.
"""

import datetime
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import infinity_core.api as api
from infinity_core.batch import Batch, submit_batch
from infinity_core.data_structures import JobParams, JobType


class ParameterValidationError(Exception):
    pass


# TODO: Figure out how to get Sphinx to not document `_generator_info`.
@dataclass(frozen=False)
class Session:
    """An encapsulation of a user session to interact with the Infinity API.

    Args:
        token: Use authentication token.
        generator: Target generator for the session.
        server: URL of the target API server.
        batches: List of accumulated batch submitted during the session.
    """

    token: str
    generator: str
    server: str = api.DEFAULT_SERVER
    batches: List[Batch] = field(default_factory=list)
    _generator_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._generator_info = api.get_single_generator_data(
            token=self.token, generator_name=self.generator, server=self.server
        ).json()

    def _validate_params(self, user_params: JobParams) -> Optional[str]:
        ty_str_to_allowed_python_ty_set: Dict[str, Set[Any]] = {
            "str": set([str]),
            "int": set([int]),
            "float": set([float]),
            "bool": set([bool]),
            "uuid": set([str, type(None)]),
        }
        pinfo = self.parameter_info
        valid_parameter_set = set(pinfo.keys())
        unsupported_parameter_set = set()
        type_violation_list = list()
        constraint_violation_list = list()
        for uk, uv in user_params.items():
            if uk not in valid_parameter_set:
                unsupported_parameter_set.add(uk)
                continue
            expected_types = ty_str_to_allowed_python_ty_set[pinfo[uk]["type"]]
            is_proper_type = any([isinstance(uv, ty) for ty in expected_types])
            if not is_proper_type:
                type_violation_list.append((uk, type(uv), expected_types))
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
        violated_types = False if len(type_violation_list) == 0 else True
        violated_constraints = False if len(constraint_violation_list) == 0 else True

        if not had_unsupported_parameter and not violated_types and not violated_constraints:
            return None
        else:
            error_string = ""
            if had_unsupported_parameter:
                error_string += "\n\nUnsupported parameters:\n"
                for p in unsupported_parameter_set:
                    error_string += f"`{p}`"
            if violated_types:
                error_string += "\n\nType violations:\n"
                for p, a, e in type_violation_list:
                    error_string += f"Input parameter `{p}` expected one of compatible type(s) `{e}`, got `{a}`\n"
            if violated_constraints:
                error_string += "\n\nConstraint violations:\n"
                for p, c, cv, pv in constraint_violation_list:
                    error_string += f"Input parameter `{p}` violated constraint `{c}` ({cv}) with value {pv}\n"
            return error_string

    def validate_job_params(self, job_params: List[JobParams]) -> List[Optional[str]]:
        """Check if a list of job parameters is valid.

        Args:
            job_params: A :obj:`list` of :obj:`dict`\s containing job parameters for the batch.

        Returns:
            A list of validation errors (one per job param dict). Values will all be `None` if everything is valid.
        """
        return [self._validate_params(jp) for jp in job_params]

    # TODO: Make cached property that is compatible with 3.7+ and satisfies `mypy`.
    @property
    def parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """`dict`: Parameters of the generator with metadata."""
        pdict = dict()
        for p in self._generator_info["params"]:
            # TODO: Should we force-error if some of these are not provided?
            ty = p.get("type")
            dv = p.get("default_value")
            op = p.get("options")
            pdict[p["name"]] = {"type": ty, "default_value": dv, "options": op}

        return pdict

    # TODO: Make cached property that is compatible with 3.7+ and satisfies `mypy`.
    @property
    def default_job(self) -> JobParams:
        """:obj:`JobParams`: Default values for parameters of the generator."""
        return {k: d["default_value"] for k, d in self.parameter_info.items()}

    def random_job(self) -> JobParams:
        """Generate job parameters using uniform random sampling.

        This function will draw parameter values from a uniform distribution for all job parameters
        associated with a `min` and `max` constraint value or with a finite set of `choices`. For
        any parameters without these properties, the default value will be used.

        Returns:
            :obj:`JobParams` containing the randomly sampled parameters.
        """
        job_params: JobParams = dict()
        for k, v in self.parameter_info.items():
            if "options" in v.keys() and v["options"] is not None:
                if "choices" in v["options"]:
                    job_params[k] = random.choice(v["options"]["choices"])
                elif "min" in v["options"] and "max" in v["options"]:
                    mn, mx = v["options"]["min"], v["options"]["max"]
                    if v["type"] == "int":
                        job_params[k] = random.randint(mn, mx)
                    elif v["type"] == "float":
                        job_params[k] = random.uniform(mn, mx)
                    else:
                        job_params[k] = v["default_value"]
                else:
                    job_params[k] = v["default_value"]
            else:
                job_params[k] = v["default_value"]

        return job_params

    def submit(
        self,
        job_params: List[JobParams],
        is_preview: bool = False,
        random_sample: bool = True,
        batch_name: Optional[str] = None,
    ) -> Batch:
        """Submit a batch of 1 or more synthetic data batch jobs to the Infinity API.

        Args:
            job_params: A :obj:`list` of :obj:`dict` containing job parameters for the batch.
            is_preview: Flag to indicate a preview is desired instead of a full job (e.g., video).
            random_sample: Flag indicating whether to poplate unspecified params with random samples or default values.
            batch_name: Optional descriptive for the submission.

        Returns:
            The created :obj:`Batch` instance.

        Raises:
            ParameterValidationError: If supplied parameters are not supported by the generator.
        """
        if is_preview:
            previews_allowed = False
            if "options" in self._generator_info:
                if "preview" in self._generator_info["options"]:
                    if self._generator_info["options"]["preview"] is True:
                        previews_allowed = True
            if not previews_allowed:
                raise ValueError(f"Previews are not supported for `{self.generator}`")

        # Check just the user-supplied errors.
        user_input_errors = self.validate_job_params(job_params=job_params)
        if not all([v is None for v in user_input_errors]):
            raise ParameterValidationError(user_input_errors)

        complete_params = []
        for jp in job_params:
            if random_sample:
                complete_params.append({**self.random_job(), **jp})
            else:
                complete_params.append({**self.default_job, **jp})

        # Check total populated errors as well. TODO: Should we do this?
        errors = self.validate_job_params(job_params=complete_params)
        if not all([v is None for v in errors]):
            raise ParameterValidationError(errors)

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

    def batch_from_api(self, batch_id: str) -> Batch:
        """Reconstruct a previously submitted batch by unique ID.

        Args:
            batch_id: Unique batch ID of the target batch.

        Returns:
            A :obj:`Batch` instance for the target batch submission.
        """
        return Batch.from_api(token=self.token, batch_id=batch_id, server=self.server)

    def get_batches_last_n_days(self, n_days: int) -> List[Dict[str, Any]]:
        """Query the API for a list of batches submitted in the last N days.

        Args:
            n_days: Number of days looking back to gather submitted batches.

        Returns:
            A :obj:`list` containing batches and their metadata.
        """
        end_time = datetime.datetime.now().astimezone()
        start_time = end_time - datetime.timedelta(days=n_days)
        r = api.get_batch_list(token=self.token, start_time=start_time, end_time=end_time, server=self.server)
        r.raise_for_status()
        data: List[Dict[str, Any]] = r.json()
        for batch in data:
            batch["created"] = datetime.datetime.fromisoformat(batch["created"])

        return data

    def get_usage_stats_last_n_days(self, n_days: int) -> Dict[str, Any]:
        """Query the API for usage stats over the last N days.

        Args:
            n_days: Number of days looking back to gather usage stats for.

        Returns:
            A :obj:`dict` containing usage stats by generator.

        Raises:
            HTTPError: When the API query returns with an error status code.
        """
        r = api.get_usage_last_n_days(token=self.token, n_days=n_days, server=self.server)
        r.raise_for_status()
        return dict(r.json())
