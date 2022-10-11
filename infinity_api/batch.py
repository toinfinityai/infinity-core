""" Infinity AI synthetic data batch module.

This module provides data structures and associated functionality to abstract over the concept of
batch submission/generation for Infinity synthetic data. Use this module's abstractions to generate,
track, and manipulate batches of synthetic data.
"""

from typing import Any, Dict, Optional, List, Tuple, Union
from datetime import datetime
import time
from dataclasses import dataclass, replace
from pathlib import Path

from serde import serialize, deserialize, field
from serde.json import from_json, to_json
import requests

from infinity_api.data_structures import JobType, SuccessfulJobRequest, FailedJobRequest, CompletedJob
import infinity_api.api as api


def _submit_jobs(
    token: str,
    generator: str,
    job_type: JobType,
    job_params: List[Dict[str, Any]],
    output_dir: str,
    timestamp: str,
    batch_folder_suffix: Optional[str] = None,
    batch_uid: Optional[str] = None,
    server: str = api.DEFAULT_SERVER,
    request_delay: float = 0.05,
    write_temp_file: bool = True,
) -> Tuple[str, List[SuccessfulJobRequest], List[FailedJobRequest], Path]:

    if job_type == JobType.PREVIEW:
        post_fn = api.post_preview
    elif job_type == JobType.STANDARD:
        post_fn = api.post_standard_job
    else:
        raise ValueError(f"Unsupported job type for batch submission: {job_type}")

    jidx = 0
    successful_requests: List[SuccessfulJobRequest] = []
    failed_requests: List[FailedJobRequest] = []
    if batch_uid is None:
        # Submit jobs until first success to get batch ID from the backend.
        for params in job_params:
            json_data = {"name": generator, "param_values": params}
            r = post_fn(token=token, json_data=json_data, server=server)
            jidx += 1
            if r.ok:
                json_payload = r.json()
                batch_uid = json_payload["batch_id"]
                job_id = json_payload["id"]
                successful_requests.append(SuccessfulJobRequest(job_id=job_id, params=params))
                if write_temp_file:
                    temp_file_path = PartialBatch(
                        uid=batch_uid,
                        folder_suffix=batch_folder_suffix,
                        submitted_jobs=successful_requests,
                        unsubmitted_jobs=job_params[jidx:],
                        failed_requests=failed_requests,
                        timestamp=timestamp,
                        generator=generator,
                        server=server,
                        job_type=job_type,
                        output_dir=output_dir,
                    ).write_temp_file()
                break
            else:
                failed_requests.append(FailedJobRequest(status_code=r.status_code, params=params))
                if write_temp_file:
                    temp_file_path = PartialBatch(
                        uid=batch_uid,
                        folder_suffix=batch_folder_suffix,
                        submitted_jobs=successful_requests,
                        unsubmitted_jobs=job_params[jidx:],
                        failed_requests=failed_requests,
                        timestamp=timestamp,
                        generator=generator,
                        server=server,
                        job_type=job_type,
                        output_dir=output_dir,
                    ).write_temp_file()
            time.sleep(request_delay)
        else:
            try:
                r.raise_for_status()
            except Exception as e:
                raise ValueError(f"All batch jobs failed in submission; last error: {e}")
            else:
                raise ValueError("All batch jobs failed in submission")

    # Submit the rest of the jobs with the obtained unique batch ID.
    for params in job_params[jidx:]:
        json_data = {"name": generator, "param_values": params, "batch_id": batch_uid}
        r = post_fn(token=token, json_data=json_data, server=server)
        jidx += 1
        if r.ok:
            job_id = r.json()["id"]
            successful_requests.append(SuccessfulJobRequest(job_id=job_id, params=params))
        else:
            failed_requests.append(FailedJobRequest(status_code=r.status_code, params=params))
        if write_temp_file:
            temp_file_path = PartialBatch(
                uid=batch_uid,
                folder_suffix=batch_folder_suffix,
                submitted_jobs=successful_requests,
                unsubmitted_jobs=job_params[jidx:],
                failed_requests=failed_requests,
                timestamp=timestamp,
                generator=generator,
                server=server,
                job_type=job_type,
                output_dir=output_dir,
            ).write_temp_file()
        time.sleep(request_delay)

    return batch_uid, successful_requests, failed_requests, temp_file_path


@serialize
@deserialize
@dataclass(frozen=True)
class PartialBatch:
    """An encapsulation of a synthetic data batch partially submitted to the Infinity API.

    This class is intended to capture partial state of batch submission interrupted on the host
    side so that it may be later resumed.

    Args:
        uid: Unique batch ID.
        folder_suffix: Descriptive suffix for batch folder stored on disk.
        submitted_jobs: Jobs submitted to the API successfully.
        unsubmitted_jobs: Jobs not yet submitted to the API.
        failed_requests: Job requests that failed at API submission.
        timestamp: Timestamp associated with *local* batch creation.
        generator: Name of the generator associated with the batch.
        server: URL of the target API server.
        job_type: Type of job in the batch.
        output_dir: Target output directory as a string.
    """

    uid: Optional[str]
    folder_suffix: Optional[str]
    submitted_jobs: List[SuccessfulJobRequest]
    unsubmitted_jobs: List[Dict[str, Any]]
    failed_requests: List[FailedJobRequest]
    timestamp: str
    generator: str
    server: str
    job_type: JobType
    output_dir: str

    @property
    def batch_dir(self) -> str:
        """str: Fully constructed partial batch output directory."""
        if self.folder_suffix:
            return f"_partial_{self.timestamp}_{self.folder_suffix[0:30]}"
        else:
            return f"_partial_{self.timestamp}"

    @property
    def num_successfully_submitted_jobs(self) -> int:
        """`int` Number of successfully submitted job requests."""
        return len(self.submitted_jobs)

    @property
    def num_unsubmitted_jobs(self) -> int:
        """`int` Number of successfully submitted job requests."""
        return len(self.unsubmitted_jobs)

    @property
    def num_failed_job_submissions(self) -> int:
        """`int` Number of job requests that failed."""
        return len(self.failed_requests)

    def to_json(self) -> str:
        """Serialize the batch data structure to a JSON string.

        Returns:
            JSON string containing serialized batch data.
        """
        return to_json(self, indent=4)

    @classmethod
    def from_batch_file(cls, json_file_path: Union[str, Path]) -> "PartialBatch":
        """Deserialize a JSON partial batch file into a :obj:`PartialBatch`.

        Args:
            json_file_path: Path to a JSON file storing a previously constructed partial batch's
                information.

        Returns:
            The deserialized :obj:`PartialBatch`.
        """
        with open(json_file_path, "r") as f:
            json_str = f.read()
        return cls.from_json(json_str=json_str)

    @classmethod
    def from_json(cls, json_str: str) -> "PartialBatch":
        """Deserialize a JSON string into a :obj:`PartialBatch`.

        Args:
            json_str: JSON string containing a previously serialized partial batch's information.

        Returns:
            The deserialized :obj:`Batch`.
        """
        deserialized_batch = from_json(cls, json_str)
        return replace(deserialized_batch)

    def write_temp_file(self) -> Path:
        """Write the partial batch to file (intended as a temporary file).

        Returns:
            The path to the written partial batch file.
        """
        partial_batch_path = Path(self.output_dir) / f"{self.batch_dir}"
        partial_batch_path.mkdir(exist_ok=True)
        serialized_batch_file = partial_batch_path / "_partial_batch.json"
        with open(serialized_batch_file, "w") as f:
            f.write(self.to_json())

        return serialized_batch_file

    def resume_submission(self, token: str, write_to_file: bool = True) -> Tuple["Batch", Optional[Path]]:
        """Resume submission of the partially submitted batch.

        Args:
            token: API authentication token.

        Returns:
            The fully submitted :obj:`Batch`.
        """
        batch_uid, successful_requests, failed_requests, temp_file_path = _submit_jobs(
            token=token,
            generator=self.generator,
            job_type=self.job_type,
            job_params=self.unsubmitted_jobs,
            output_dir=self.output_dir,
            timestamp=self.timestamp,
            batch_folder_suffix=self.folder_suffix,
            batch_uid=self.uid,
            server=self.server,
            write_temp_file=True,
        )

        batch = Batch(
            uid=batch_uid,
            timestamp=self.timestamp,
            folder_suffix=self.folder_suffix,
            jobs=successful_requests,
            failed_requests=failed_requests,
            generator=self.generator,
            server=self.server,
            job_type=self.job_type,
            token=token,
            output_dir=self.output_dir,
        )

        if temp_file_path is not None:
            temp_file_path.unlink()

        batch_path = batch.write_to_file() if write_to_file else None

        return batch, batch_path

    def truncate_to_batch(self, token: str) -> "Batch":
        """Convert partial batch to full batch by truncating the unsubmitted jobs.

        Args:
            token: API authentication token.

        Returns:
            A full :obj:`Batch` omitting unsubmitted jobs from the original submission attempt.
        """
        if self.uid is None:
            raise ValueError("No successful jobs submitted to API; there is no `batch`")

        return Batch(
            uid=self.uid,
            timestamp=self.timestamp,
            folder_suffix=self.folder_suffix,
            jobs=self.submitted_jobs,
            failed_requests=self.failed_requests,
            generator=self.generator,
            server=self.server,
            job_type=self.job_type,
            output_dir=self.output_dir,
            token=token,
        )


@serialize
@deserialize
@dataclass(frozen=True)
class Batch:
    """An encapsulation of a batch of synthetic data generated from the Infinity API.

    Args:
        uid: Unique batch ID.
        timestamp: Timestamp associated with *local* batch creation.
        folder_suffix: Descriptive suffix for batch folder stored on disk.
        jobs: Jobs submitted to the API successfully.
        failed_requests: Job requests that failed at API submission.
        generator: Name of the generator associated with the batch.
        server: URL of the target API server.
        job_type: Type of job in the batch.
        output_dir: Target output directory as a string.
        token: API authentication token.
    """

    uid: str
    timestamp: str
    folder_suffix: Optional[str]
    jobs: List[SuccessfulJobRequest]
    failed_requests: List[FailedJobRequest]
    generator: str
    server: str
    job_type: JobType
    output_dir: str
    token: str = field(default="", metadata={"serde_skip": True})

    @property
    def batch_dir(self) -> str:
        """str: Fully constructed batch output directory."""
        if self.folder_suffix:
            return f"{self.timestamp}_{self.folder_suffix[0:30]}"
        else:
            return f"{self.timestamp}"

    @property
    def job_ids(self) -> List[str]:
        """:obj:`list` of :obj:`str`: List of job IDs for successfully submitted job requests."""
        return [j.job_id for j in self.jobs]

    @property
    def num_successfully_submitted_jobs(self) -> int:
        """`int` Number of successfully submitted job requests."""
        return len(self.jobs)

    @property
    def num_failed_job_submissions(self) -> int:
        """`int` Number of job requests that failed."""
        return len(self.failed_requests)

    def to_json(self) -> str:
        """Serialize the batch data structure to a JSON string.

        Returns:
            JSON string containing serialized batch data.
        """
        return to_json(self, indent=4)

    @classmethod
    def from_batch_file(cls, json_file_path: Union[str, Path], token: str) -> "Batch":
        """Deserialize a JSON batch file into a :obj:`Batch`.

        Args:
            json_file_path: Path to a JSON file storing a previously constructed batch's
                information.
            token: API authentication token associated with the batch.

        Returns:
            The deserialized :obj:`Batch`.
        """
        with open(json_file_path, "r") as f:
            json_str = f.read()
        return cls.from_json(json_str=json_str, token=token)

    @classmethod
    def from_batch_folder(cls, batch_folder_path: Union[str, Path], token: str) -> "Batch":
        """Deserialize a JSON batch file from a given folder path into a :obj:`Batch`.

        Args:
            batch_folder_path: Path to a folder containing a serialized `batch.json` JSON file
                storing a previously constructed batch's information.
            token: API authentication token associated with the batch.

        Returns:
            The deserialized :obj:`Batch`.
        """
        json_file_path = Path(batch_folder_path) / "batch.json"
        return cls.from_batch_file(json_file_path=json_file_path, token=token)

    @classmethod
    def from_json(cls, json_str: str, token: str) -> "Batch":
        """Deserialize a JSON string into a :obj:`Batch`.

        Args:
            json_str: JSON string containing a previously serialized batch's information.
            token: API authentication token associated with the batch.

        Returns:
            The deserialized :obj:`Batch`.
        """
        deserialized_batch = from_json(cls, json_str)
        return replace(deserialized_batch, token=token)

    def get_batch_data(self) -> requests.models.Response:
        """Return data from the API for each job in the batch.

        Returns:
            :obj:`requests.models.Response` from querying the API.

        Raises:
            ValueError: If the :obj:`JobType` associated with the batch is unsupported by the API.
        """
        if self.job_type == JobType.PREVIEW:
            return api.get_batch_preview_job_data(token=self.token, batch_id=self.uid, server=self.server)
        elif self.job_type == JobType.STANDARD:
            return api.get_batch_standard_job_data(token=self.token, batch_id=self.uid, server=self.server)
        else:
            raise ValueError(f"Unsupported job type `{self.job_type}` for querying batch data")

    def get_completed_jobs(self) -> List[CompletedJob]:
        """Returns a list of completed batch jobs.

        Returns:
            :obj:`list` of :obj:`CompletedJob` A list of currently completed batch jobs.

        Raises:
            HTTPError: When querying the batch jobs returns an error status code.
        """
        r = self.get_batch_data()
        r.raise_for_status()

        completed_job_payloads = [j for j in r.json() if not j["in_progress"]]

        # Return results in the original (`self.jobs`) job order.
        completed_job_payloads_dict = {j["id"]: j for j in completed_job_payloads}
        completed_jobs_id_set = set(completed_job_payloads_dict.keys())
        completed_job_info_in_original_order = [
            (j.job_id, j.params) for j in self.jobs if j.job_id in completed_jobs_id_set
        ]

        completed_jobs = []
        for jid, jparams in completed_job_info_in_original_order:
            job_result_url = completed_job_payloads_dict[jid]["result_url"]
            completed_jobs.append(CompletedJob(job_id=jid, params=jparams, result_url=job_result_url))

        return completed_jobs

    def get_completed_jobs_valid_and_invalid(
        self,
    ) -> Tuple[List[CompletedJob], List[CompletedJob]]:
        """Returns completed batch split by valid status.

        Returns:
            A tuple containing a list of valid completed jobs and a list of invalid completed jobs.
            A job may complete with an error or otherwise invalid state such that, for example,
            a final output was not rendered. A "valid" job here means the final output is
            available.
        """
        completed_valid_jobs = []
        completed_invalid_jobs = []
        completed_jobs = self.get_completed_jobs()
        for cj in completed_jobs:
            if cj.result_url:
                completed_valid_jobs.append(cj)
            else:
                completed_invalid_jobs.append(cj)

        return completed_valid_jobs, completed_invalid_jobs

    def await_jobs(self, timeout: int = 48 * 60 * 60, polling_interval: float = 10) -> List[CompletedJob]:
        """Serially poll and wait for all jobs in the batch to complete (blocking).

        Note: This function will hang forever if a backend error leads to a hung job
        (that never completes).

        Args:
            timeout: Maximum allowable time to wait for jobs in batch to complete (in seconds).
                Defaults to 48 hours.
            polling_interval: Time interval to sleep (in seconds) between consecutive iterations
                of polling. Defaults to 10 seconds.

        Returns:
            :obj:`list` of all :obj:`CompletedJobs` in batch.

        Raises:
            HTTPError: When querying the batch jobs returns an error status code.
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
            r = self.get_batch_data()
            r.raise_for_status()
            completed_job_payloads = [j for j in r.json() if not j["in_progress"]]
            num_completed_jobs = len(completed_job_payloads)
            if (datetime.now() - start_time).seconds > timeout:
                raise TimeoutError()
            time.sleep(polling_interval)

        duration = datetime.now() - start_time
        print(f"Duration for all jobs: {duration.seconds} [s]")

        # Return results in the original (`self.jobs`) job order.
        job_info = [(j.job_id, j.params) for j in self.jobs]
        completed_job_payloads_dict = {j["id"]: j for j in completed_job_payloads}
        completed_jobs = []
        for jid, jparams in job_info:
            job_result_url = completed_job_payloads_dict[jid]["result_url"]
            completed_jobs.append(CompletedJob(job_id=jid, params=jparams, result_url=job_result_url))

        return completed_jobs

    def write_to_file(self) -> Path:
        batch_path = Path(self.output_dir) / f"{self.batch_dir}"
        batch_path.mkdir(exist_ok=True)
        serialized_batch_file = batch_path / "batch.json"
        with open(serialized_batch_file, "w") as f:
            f.write(self.to_json())

        return serialized_batch_file


def submit_batch_to_api(
    token: str,
    generator: str,
    job_type: JobType,
    job_params: List[Dict[str, Any]],
    output_dir: str,
    batch_folder_suffix: Optional[str] = None,
    server: str = api.DEFAULT_SERVER,
    write_to_file: bool = True,
    request_delay: float = 0.05,
) -> Tuple[Batch, Optional[Path]]:
    """Submits a batch of jobs to the Infinity API.

    Args:
        token: API authentication token associated with the batch.
        generator: Name of the generator associated with the batch.
        job_type: Type of job requested in the batch.
        job_params: :obj:`list` of :obj:`dict` containing input parameters for each job of the
            batch.
        output_dir: Target output directory of the batch, as a string.
        batch_folder_suffix: Optional descriptive suffix for batch folder stored on disk.
        server: URL of the target API server.
        write_to_file: Flag to serialize batch information to disk as a JSON file.
        request_delay: Delay in seconds between job request submissions for each job in the batch.
            Defaults to 50 milliseconds.

    Returns:
        Tuple of the created :obj:`Batch` instance and a path to its metadata on disk.

    Raises:
        ValueError: If an unsupported job type is requested.
        ValueError: If all batch jobs fail at submission.
    """

    if token == "":
        raise ValueError("`token` cannot be an empty string")
    if generator == "":
        raise ValueError("`generator` cannot be an empty string")

    batch_time = datetime.now()
    batch_timestamp = batch_time.strftime("%Y%m%d_T%H%M%S%f")

    print("Submitting jobs to API...")

    batch_uid, successful_requests, failed_requests, temp_file_path = _submit_jobs(
        token=token,
        generator=generator,
        job_type=job_type,
        job_params=job_params,
        output_dir=output_dir,
        timestamp=batch_timestamp,
        batch_uid=None,
        server=server,
        request_delay=request_delay,
        write_temp_file=True,
    )

    batch = Batch(
        uid=batch_uid,
        timestamp=batch_timestamp,
        folder_suffix=batch_folder_suffix,
        jobs=successful_requests,
        failed_requests=failed_requests,
        generator=generator,
        server=server,
        job_type=job_type,
        token=token,
        output_dir=output_dir,
    )

    if temp_file_path is not None:
        temp_file_path.unlink()

    batch_path = batch.write_to_file() if write_to_file else None

    return batch, batch_path
