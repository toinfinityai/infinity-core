""" Infinity AI synthetic data batch module.

This module provides data structures and associated functionality to abstract over the concept of
batch submission/generation for Infinity synthetic data. Use this module's abstractions to generate,
track, and manipulate batches of synthetic data.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

import infinity_api.api as api
from infinity_api.data_structures import CompletedJob, JobParams, JobType


class BatchJobTypeError(Exception):
    pass


class BatchRetrievalError(Exception):
    pass


def _parse_jobs_from_response_data(json_data: Dict[str, Any], token: str, server: str) -> JobParams:
    # TODO: Find a better way to deal with this.
    generator = json_data["job_runs"][0]["name"]
    r2 = api.get_single_generator_data(token=token, generator_name=generator, server=server)
    r2.raise_for_status()
    param_names = set([p["name"] for p in r2.json()["params"]])
    save_state = True if "state" in param_names else False

    jobs = {}
    # TODO: Backend needs to return properly typed JSON.
    for jr in json_data["job_runs"]:
        params = jr["param_values"]
        jid = jr["id"]
        if save_state:
            params["state"] = jid
        jobs[jid] = params

    return jobs


@dataclass(frozen=True)
class Batch:
    """An encapsulation of a batch of synthetic data generated from the Infinity API.

    Args:
        token: User authentication token.
        uid: Unique batch ID.
        name: Short description of the batch.
        jobs: Jobs submitted to the API successfully as uid:JobParams dict entries.
        server: URL of the target API server.
        job_type: Type of job in the batch.
    """

    token: str
    uid: str
    name: str
    jobs: Dict[str, JobParams]
    server: str
    job_type: JobType

    @property
    def job_ids(self) -> List[str]:
        """:obj:`list` of :obj:`str`: List of job IDs for jobs in the batch."""
        return list(self.jobs.keys())

    @property
    def job_params(self) -> List[JobParams]:
        """:obj:`list` of :obj:`JobParams`: List of job parameters for jobs in the batch."""
        return list(self.jobs.values())

    @property
    def num_jobs(self) -> int:
        """`int` Number of successfully submitted job requests."""
        return len(self.jobs)

    def get_num_jobs_remaining(self) -> int:
        # TODO: Update doc string as no longer a property.
        """`int` Number of jobs still in prgoress for the batch."""
        data = self.get_batch_data().json()
        num_completed = 0
        for jr in data["job_runs"]:
            if not jr["in_progress"]:
                num_completed += 1

        return self.num_jobs - num_completed

    def get_batch_data(self) -> requests.models.Response:
        """Get detailed batch data from the API server.

        Returns:
            HTTP request response.

        Raises:
            HTTPError: If the API query fails.
        """
        r = api.get_batch_data(token=self.token, batch_id=self.uid, server=self.server)
        r.raise_for_status()
        if len(r.json()) > 0:
            return r
        else:
            raise BatchRetrievalError(f"Batch `{self.uid}` does not exist")

    def get_batch_summary(self) -> requests.models.Response:
        """Get batch summary data from the API server.

        Returns:
            HTTP request response.

        Raises:
            HTTPError: If the API query fails.
            BatchJobTypeError: If the batch is associated with an unsupported job type.
        """
        # TODO: Implement with summary endpoint when available.
        return self.get_batch_data()

    @classmethod
    def from_api(cls, token: str, batch_id: str, server: str = api.DEFAULT_SERVER) -> "Batch":
        """Create a `Batch` instance by querying the API.

        Args:
            token: User authentication token.
            batch_id: Unique ID associated with a previously run batch.
            server: Base server URL.

        Returns:
            A :obj:`Batch` created with information from the API.

        Raises:
            HTTPError: If the API query fails.
        """
        r = api.get_batch_data(token=token, batch_id=batch_id, server=server)
        r.raise_for_status()
        data = r.json()
        batch_id = data["id"]
        job_type = JobType.PREVIEW if data["job_runs"][0]["is_preview"] else JobType.STANDARD
        jobs = _parse_jobs_from_response_data(data, token=token, server=server)
        name = data["name"]

        return cls(token=token, uid=batch_id, name=name, jobs=jobs, server=server, job_type=job_type)

    def get_completed_jobs(self) -> List[CompletedJob]:
        """Returns a list of completed batch jobs.

        Returns:
            :obj:`list` of :obj:`CompletedJob` A list of currently completed batch jobs.
        """
        data = self.get_batch_data().json()

        # TODO: Compared to previous, this may lose the order of the original jobs, if that is/was important.
        # TODO: Can the backend ensure ordering is preserved?
        completed_jobs = []
        for jr in data["job_runs"]:
            completed_jobs.append(
                CompletedJob(
                    uid=jr["id"], generator=jr["name"], params=self.jobs[jr["id"]], result_url=jr["result_url"]
                )
            )

        return completed_jobs

    def get_valid_completed_jobs(
        self,
    ) -> List[CompletedJob]:
        """Returns only valid completed jobs (with valid result URL).

        Returns:
            A list of valid completed jobs. A job may complete with an error or otherwise invalid
            state such that, for example, a final output was not rendered. A "valid" job here
            means the final output is available.
        """
        return [cj for cj in self.get_completed_jobs() if cj.result_url]

    def await_completion(self, polling_interval: float = 10) -> List[CompletedJob]:
        """Serially poll and wait for all jobs in the batch to complete (blocking).

        WARNING: This function will hang forever if a backend error leads to a hung job
        (that never completes).

        Args:
            polling_interval: Time interval to sleep (in seconds) between consecutive iterations
                of polling. Defaults to 10 seconds.

        Returns:
            :obj:`list` of all :obj:`CompletedJobs` in batch.
        """
        num_jobs = len(self.jobs)
        if num_jobs == 0:
            return []
        start_time = datetime.now()
        num_jobs_remaining = self.num_jobs

        while num_jobs_remaining > 0:
            num_jobs_remaining = self.get_num_jobs_remaining()
            elapsed_time = int((datetime.now() - start_time).seconds)
            print(f"{num_jobs_remaining} remaining jobs [{elapsed_time:d} s]...\t\t\t", end="\r")
            time.sleep(polling_interval)

        duration = datetime.now() - start_time
        print(f"Duration for all jobs: {duration.seconds} [s]")

        # Return results in the original (`self.jobs`) job order.
        # TODO: Update the following to work as expected with new querying.
        # TODO: Removed guarantee of same order as in `self.jobs`; is that OK?
        return self.get_valid_completed_jobs()


def submit_batch(
    token: str,
    generator: str,
    job_type: JobType,
    job_params: List[Dict[str, Any]],
    name: Optional[str] = None,
    server: str = api.DEFAULT_SERVER,
) -> Batch:
    """Submits a batch of jobs to the Infinity API.

    Args:
        token: API authentication token associated with the batch.
        generator: Name of the generator associated with the batch.
        job_type: Type of job requested in the batch.
        job_params: :obj:`list` of :obj:`dict` containing input parameters for each job of the
            batch.
        server: URL of the target API server.

    Returns:
        :obj:`Batch` instance from successful API submission.

    Raises:
        ValueError: If `token` or `generator` is empty.
        HTTPError: If batch submission post fails.
        BatchJobTypeError: If an unsupported job type is used.
    """

    if token == "":
        raise ValueError("`token` cannot be an empty string")
    if generator == "":
        raise ValueError("`generator` cannot be an empty string")
    name = "" if name is None else name

    print("Submitting batch of jobs to the API...")

    is_preview = True if job_type == JobType.PREVIEW else False
    r = api.post_batch(
        token=token, generator=generator, name=name, job_params=job_params, is_preview=is_preview, server=server
    )
    r.raise_for_status()
    response_data = r.json()
    batch_id = response_data["id"]
    jobs = _parse_jobs_from_response_data(json_data=response_data, token=token, server=server)

    # TODO Implement this based on post response details.
    return Batch(token=token, uid=batch_id, name=name, jobs=jobs, server=server, job_type=job_type)
