from typing import Dict, Optional, List, Tuple
from datetime import datetime
import time
from dataclasses import dataclass, replace
from pathlib import Path

from serde import serde, serialize, deserialize, field
from serde.json import from_json, to_json
import requests

from infinity_api.data_structures import SuccessfulJobRequest, FailedJobRequest, CompletedJob


@serialize
@deserialize
@dataclass(frozen=True)
class Batch:
    uid: str
    timestamp: str
    batch_folder_suffix: Optional[str]
    jobs: List[SuccessfulJobRequest]
    failed_requests: List[FailedJobRequest]
    generator: str
    server: str
    jobs_query_endpoint: str
    batch_query_endpoint: str
    output_dir: str
    token: str = field(default="", metadata={"serde_skip": True})

    @property
    def batch_dir(self) -> str:
        if self.batch_folder_suffix:
            return f"{self.timestamp}_{self.batch_folder_suffix[0:30]}"
        else:
            return f"{self.timestamp}"

    @property
    def job_ids(self) -> List[str]:
        return [j.job_id for j in self.jobs]

    @property
    def num_successfully_submitted_jobs(self) -> int:
        return len(self.job_ids)

    def to_json(self) -> str:
        return to_json(self, indent=4)

    @classmethod
    def from_batch_file(cls, json_file_path: str, token: str) -> "Batch":
        with open(json_file_path, "r") as f:
            json_str = f.read()
        return cls.from_json(json_str=json_str, token=token)

    @classmethod
    def from_batch_folder(cls, batch_folder_path: str, token: str) -> "Batch":
        json_file_path = Path(batch_folder_path) / "batch.json"
        return cls.from_batch_file(json_file_path=json_file_path, token=token)

    @classmethod
    def from_json(cls, json_str: str, token: str) -> "Batch":
        deserialized_batch = from_json(cls, json_str)
        return replace(deserialized_batch, token=token)

    def get_completed_jobs(self) -> List[CompletedJob]:
        """Returns list of completed jobs in the batch."""
        r = requests.get(
            f"{self.server}{self.batch_query_endpoint}",
            headers={"Authorization": f"Token {self.token}"},
        )
        completed_job_payloads = [j for j in r.json() if not j["in_progress"]]

        # Construct dict and loop through completed `job_ids` to preserve order of `self.jobs`.
        completed_job_payloads_dict = {j["id"]: j for j in completed_job_payloads}
        completed_jobs_id_set = set(completed_job_payloads_dict.keys())
        completed_job_ids = [j.job_id for j in self.jobs if j.job_id in completed_jobs_id_set]
        completed_job_params_dict = {j.job_id: j.params for j in self.jobs if j.job_id in completed_jobs_id_set}
        completed_jobs = []
        for jid in completed_job_ids:
            job_result_url = completed_job_payloads_dict[jid]["result_url"]
            params = completed_job_params_dict[jid]
            completed_jobs.append(CompletedJob(job_id=jid, params=params, result_url=job_result_url))

        return completed_jobs

    def get_completed_jobs_valid_and_invalid(
        self,
    ) -> Tuple[List[CompletedJob], List[CompletedJob]]:
        """Returns tuple of valid and invalid `CompletedJob` objects."""
        completed_valid_jobs = []
        completed_invalid_jobs = []
        completed_jobs = self.get_completed_jobs()
        for cj in completed_jobs:
            if cj.result_url:
                completed_valid_jobs.append(cj)
            else:
                completed_invalid_jobs.append(cj)
        return completed_valid_jobs, completed_invalid_jobs

    def await_jobs(self, timeout: int = 3 * 60 * 60, polling_interval: float = 10) -> List[CompletedJob]:
        """Waits for all jobs in batch to complete.

        Args:
            timeout: Maximum allowable time to wait for jobs in batch to complete (in seconds).
            polling_interval: Time interval to sleep (in seconds) between consecutive iterations
                of polling.

        Returns:
            List of all `CompletedJobs` in batch.
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
            r = requests.get(
                f"{self.server}{self.batch_query_endpoint}",
                headers={"Authorization": f"Token {self.token}"},
            )
            completed_job_payloads = [j for j in r.json() if not j["in_progress"]]
            num_completed_jobs = len(completed_job_payloads)
            if (datetime.now() - start_time).seconds > timeout:
                raise TimeoutError()
            time.sleep(polling_interval)

        duration = datetime.now() - start_time
        print(f"Duration for all jobs: {duration.seconds} [s]")

        # Construct dict and loop through `job_ids` to preserve order of `self.jobs`.
        job_ids = [j.job_id for j in self.jobs]
        job_params_dict = {j.job_id: j.params for j in self.jobs}
        completed_job_payloads_dict = {j["id"]: j for j in completed_job_payloads}
        completed_jobs = []
        for jid in job_ids:
            job_result_url = completed_job_payloads_dict[jid]["result_url"]
            params = job_params_dict[jid]
            completed_jobs.append(CompletedJob(job_id=jid, params=params, result_url=job_result_url))

        return completed_jobs


def submit_batch_to_api(
    batch_folder_suffix: Optional[str],
    generator: str,
    server: str,
    run_endpoint: str,
    query_endpoint: str,
    token: str,
    output_dir: str,
    job_params: List[Dict],
    write_submission_status_to_file: bool = True,
    request_delay: float = 0.05,
) -> Tuple[Batch, Optional[str]]:
    """Submits a batch of jobs to the API.

    Args:
        request_delay: Delay between requests, s

    Returns:
        Tuple of corresponding `Batch` object and a path to its metadata on disk.
    """

    batch_time = datetime.now()
    batch_timestamp = batch_time.strftime("%Y%m%d_T%H%M%S%f")

    successful_requests = []
    failed_requests = []

    print("Submitting jobs to API...")

    # Submit jobs until first success to get batch ID from the backend.
    jidx = 0
    for params in job_params:
        r = requests.post(
            f"{server}{run_endpoint}",
            json={
                "name": generator,
                "param_values": params,
            },
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
            },
        )
        jidx += 1
        if r.status_code == 201:
            json_payload = r.json()
            batch_uid = json_payload["batch_id"]
            job_id = json_payload["id"]
            successful_requests.append(SuccessfulJobRequest(job_id=job_id, params=params))
            break
        else:
            failed_requests.append(FailedJobRequest(status_code=r.status_code, params=params))
        time.sleep(request_delay)
    else:
        raise ValueError("All batch jobs failed in submission")

    # Submit the rest of the jobs with the obtained unique batch ID.
    for params in job_params[jidx:]:
        r = requests.post(
            f"{server}{run_endpoint}",
            json={
                "name": generator,
                "param_values": params,
                "batch_id": batch_uid,
            },
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
            },
        )
        if r.status_code == 201:
            job_id = r.json()["id"]
            successful_requests.append(SuccessfulJobRequest(job_id=job_id, params=params))
        else:
            failed_requests.append(FailedJobRequest(status_code=r.status_code, params=params))
        time.sleep(request_delay)

    batch_query_endpoint = query_endpoint + f"?batch_id={batch_uid}"

    batch = Batch(
        uid=batch_uid,
        timestamp=batch_timestamp,
        batch_folder_suffix=batch_folder_suffix,
        jobs=successful_requests,
        failed_requests=failed_requests,
        generator=generator,
        server=server,
        jobs_query_endpoint=query_endpoint,
        batch_query_endpoint=batch_query_endpoint,
        token=token,
        output_dir=output_dir,
    )

    if write_submission_status_to_file:
        batch_path = Path(output_dir) / f"{batch.batch_dir}"
        batch_path.mkdir(exist_ok=False)
        serialized_batch_file = batch_path / "batch.json"
        with open(serialized_batch_file, "w") as f:
            f.write(batch.to_json())
    else:
        batch_path = None

    return batch, batch_path
