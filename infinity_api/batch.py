""" Infinity AI synthetic data batch module.

This module provides data structures and associated functionality to abstract over the concept of
batch submission/generation for Infinity synthetic data. Use this module's abstractions to generate,
track, and manipulate batches of synthetic data.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple

import requests

import infinity_api.api as api
from infinity_api.data_structures import CompletedJob, JobType, SubmittedJob


class BatchJobTypeError(Exception):
    pass


class BatchRetrievalError(Exception):
    pass


def _get_batch_data_raw_with_type(
    token: str, batch_id: str, job_type: JobType, server: str = api.DEFAULT_SERVER
) -> requests.models.Response:
    if job_type == JobType.PREVIEW:
        r = api.get_batch_preview_job_data(token=token, batch_id=batch_id, server=server)
        r.raise_for_status()
        if len(r.json()) > 0:
            return r
        else:
            raise BatchRetrievalError("Batch `{batch_id}` with job type `{job_type}` does not exist")
    elif job_type == JobType.STANDARD:
        r = api.get_batch_standard_job_data(token=token, batch_id=batch_id, server=server)
        r.raise_for_status()
        if len(r.json()) > 0:
            return r
        else:
            raise BatchRetrievalError("Batch `{batch_id}` with job type `{job_type}` does not exist")
    else:
        raise BatchJobTypeError("Unsupported job type `{job_type}` for batch retrieval")


def _get_batch_data_raw_unknown_type(
    token: str, batch_id: str, server: str = api.DEFAULT_SERVER
) -> Tuple[requests.models.Response, JobType]:
    try:
        return (
            _get_batch_data_raw_with_type(token=token, batch_id=batch_id, job_type=JobType.PREVIEW, server=server),
            JobType.PREVIEW,
        )
    except BatchRetrievalError:
        pass

    try:
        return (
            _get_batch_data_raw_with_type(token=token, batch_id=batch_id, job_type=JobType.STANDARD, server=server),
            JobType.STANDARD,
        )
    except BatchRetrievalError:
        pass

    raise BatchRetrievalError("Batch `{batch_id}` does not exist")


@dataclass(frozen=True)
class Batch:
    """An encapsulation of a batch of synthetic data generated from the Infinity API.

    Args:
        token: User authentication token.
        uid: Unique batch ID.
        jobs: Jobs submitted to the API successfully.
        server: URL of the target API server.
        job_type: Type of job in the batch.
    """

    token: str
    uid: str
    jobs: List[SubmittedJob]
    server: str
    job_type: JobType

    @cached_property
    def job_ids(self) -> List[str]:
        """:obj:`list` of :obj:`str`: List of job IDs for successfully submitted job requests."""
        return [j.uid for j in self.jobs]

    @property
    def num_jobs(self) -> int:
        """`int` Number of successfully submitted job requests."""
        return len(self.jobs)

    @property
    def num_remaining_jobs(self) -> int:
        """`int` Number of jobs still in prgoress for the batch."""
        # TODO: Backend must be updated to support this.
        return self.num_jobs - int(self.get_batch_summary().json()["num_completed_jobs"])

    def get_batch_data(self) -> requests.models.Response:
        """Get detailed batch data from the API server.

        Returns:
            HTTP request response.

        Raises:
            HTTPError: If the API query fails.
        """
        r = _get_batch_data_raw_with_type(
            token=self.token, batch_id=self.uid, job_type=self.job_type, server=self.server
        )
        r.raise_for_status()
        return r

    def get_batch_summary(self) -> requests.models.Response:
        """Get batch summary data from the API server.

        Returns:
            HTTP request response.

        Raises:
            HTTPError: If the API query fails.
            BatchJobTypeError: If the batch is associated with an unsupported job type.
        """
        if self.job_type == JobType.PREVIEW:
            r = api.get_batch_preview_status(token=self.token, batch_id=self.uid, server=self.server)
            r.raise_for_status()
            return r
        elif self.job_type == JobType.STANDARD:
            r = api.get_batch_standard_job_status(token=self.token, batch_id=self.uid, server=self.server)
            r.raise_for_status()
            return r
        else:
            raise BatchJobTypeError("Unsupported job type `{self.job_type}` for batch summary retrieval")

    @classmethod
    def from_api(cls, token: str, batch_id: str, server: str = api.DEFAULT_SERVER) -> "Batch":
        """Create a `Batch` instance by querying the API.

        Args:
            token: User authentication token.
            batch_id: Unique ID associated with a previously run batch.
            server: Base server URL.

        Returns:
            A :obj:`Batch` created with information from the API.
        """
        r, job_type = _get_batch_data_raw_unknown_type(token=token, batch_id=batch_id, server=server)
        data = r.json()
        jobs = []
        for j in data:
            # TODO: Backend must be updated to support grabbing of params.
            jobs.append(SubmittedJob(uid=j["id"], generator=j["job"], params=j["params"]))

        return cls(token=token, uid=batch_id, jobs=jobs, server=server, job_type=job_type)

    def get_completed_jobs(self) -> List[CompletedJob]:
        """Returns a list of completed batch jobs.

        Returns:
            :obj:`list` of :obj:`CompletedJob` A list of currently completed batch jobs.
        """
        r = self.get_batch_data()

        # TODO: Backend must be modified to support `params`.
        # TODO: Compared to previous, this may lose the order of the original jobs, if that is/was important.
        completed_jobs = []
        for j in r.json():
            completed_jobs.append(
                CompletedJob(uid=j["id"], generator=j["job"], params=j["params"], result_url=j["result_url"])
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

    def await_jobs(self, polling_interval: float = 10) -> List[CompletedJob]:
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
        num_completed_jobs = 0

        while num_completed_jobs != num_jobs:
            elapsed_time = int((datetime.now() - start_time).seconds)
            print(
                f"{num_jobs - num_completed_jobs} remaining jobs [{elapsed_time:d} s]...\t\t\t",
                end="\r",
            )
            r = self.get_batch_summary()
            # TODO: Backend must be changed to support this.
            num_completed_jobs = r.json()["num_completed_jobs"]
            time.sleep(polling_interval)

        duration = datetime.now() - start_time
        print(f"Duration for all jobs: {duration.seconds} [s]")

        # Return results in the original (`self.jobs`) job order.
        # TODO: Update the following to work as expected with new querying.
        # TODO: Removed guarantee of same order as in `self.jobs`; is that OK?
        return self.get_valid_completed_jobs()


def submit_batch_to_api(
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

    print("Submitting jobs to API...")

    is_preview = True if job_type == JobType.PREVIEW else False
    r = api.post_batch(
        token=token, generator=generator, name=name, job_params=job_params, is_preview=is_preview, server=server
    )
    r.raise_for_status()
    response_data = r.json()
    batch_id = response_data["batch_id"]

    # TODO Implement this based on post response details.
    jobs = NotImplemented
    return Batch(token=token, uid=batch_id, jobs=jobs, server=server, job_type=job_type)
