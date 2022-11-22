""" Infinity AI synthetic data batch module.

This module provides data structures and associated functionality to abstract over the concept of
batch submission/generation for Infinity synthetic data. Use this module's abstractions to generate,
track, and manipulate batches of synthetic data.
"""

import concurrent.futures
import io
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from infinity_core import api
from infinity_core.data_structures import CompletedJob, JobParams, JobType, ValidCompletedJob


class BatchJobTypeError(Exception):
    pass


class JobRetrivalError(Exception):
    pass


class DownloadError(Exception):
    pass


def _parse_jobs_from_response_data(json_data: Dict[str, Any], token: str, server: str) -> JobParams:
    # TODO: Find away to avoid having to make another request just to special-case handling of `state`.
    # This subtle behavior is used by this module to ensure `batch.job_params` provides a list of jobs
    # with the job_id set as `state` so they can be readily used to seed future batches/jobs.
    # We should re-think this approach in general and find a better long-term solution of handling
    # previous job-dependent state.
    generator = json_data["job_runs"][0]["name"]
    request_for_generator_info = api.get_single_generator_data(token=token, generator_name=generator, server=server)
    request_for_generator_info.raise_for_status()
    param_names = set([p["name"] for p in request_for_generator_info.json()["params"]])
    save_state = True if "state" in param_names else False

    jobs = {}
    for jr in json_data["job_runs"]:
        params = jr["param_values"]
        jid = jr["id"]
        if save_state:
            params["state"] = jid
        jobs[jid] = params

    return jobs


def _download_and_extract_zip(download_info: Tuple[str, str, Path]) -> None:
    url, _, target_path = download_info
    r = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(target_path)


@dataclass(frozen=True)
class Batch:
    """An encapsulation of a batch of synthetic data generated from the Infinity API.

    Args:
        token: User authentication token.
        batch_id: Unique batch ID.
        name: Short description of the batch.
        jobs: Jobs submitted to the API successfully as JobParams dict entries.
        server: URL of the target API server.
        job_type: Type of job in the batch.
    """

    token: str
    batch_id: str
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
        """Get number of jobs still in progress.

        Returns:
            Number of jobs remaining (computation in progress).
        """
        data = self.get_batch_summary_data()
        num_completed = 0
        for jr in data["job_runs"]:
            if not jr["in_progress"]:
                num_completed += 1

        return self.num_jobs - num_completed

    def get_batch_data(self) -> Any:
        """Get detailed batch data from the API server.

        Returns:
            Dictionary containing batch metadata.

        Raises:
            HTTPError: If the API query fails.
        """
        r = api.get_batch_data(token=self.token, batch_id=self.batch_id, server=self.server)
        r.raise_for_status()
        return r.json()

    def get_batch_summary_data(self) -> Any:
        """Get batch summary data from the API server.

        Returns:
            HTTP request response.

        Raises:
            HTTPError: If the API query fails.
            BatchJobTypeError: If the batch is associated with an unsupported job type.
        """
        r = api.get_batch_summary_data(token=self.token, batch_id=self.batch_id, server=self.server)
        r.raise_for_status()
        return r.json()

    def get_job_summary_data(self, job_id: str) -> Any:
        batch_summary_data = self.get_batch_summary_data()
        for jr in batch_summary_data["job_runs"]:
            if jr["id"] == job_id:
                return jr
        else:
            raise JobRetrivalError(f"Job (job ID: {job_id}) is not associated with batch (batch ID: {self.batch_id})")

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

        return cls(token=token, batch_id=batch_id, name=name, jobs=jobs, server=server, job_type=job_type)

    def get_completed_jobs(self) -> List[CompletedJob]:
        """Returns a list of completed batch jobs.

        Note: A job that resulted in an error is considered a 'completed' job. If you want a list
        of valid completed jobs where valid means completed successfully with available results,
        use the `get_valid_completed_jobs` method instead.

        Returns:
            A :obj:`list` of currently completed :obj:`Batch` :obj:`CompletedJobs`\s.
        """
        data = self.get_batch_summary_data()

        # TODO: Verify that submission order is preserved throughouth the system.
        completed_jobs = []
        for jr in data["job_runs"]:
            if not jr["in_progress"]:
                completed_jobs.append(
                    CompletedJob(
                        job_id=jr["id"], generator=jr["name"], params=self.jobs[jr["id"]], result_url=jr["result_url"]
                    )
                )

        return completed_jobs

    def get_valid_completed_jobs(
        self,
    ) -> List[ValidCompletedJob]:
        """Returns only valid completed jobs (with valid result URL).

        Returns:
            A :obj:`list` of currently completed and valid :obj:`ValidCompletedJob`\s. A job may
            complete with an error or otherwise invalid state such that, for example, a final
            output was not rendered. A "valid" job here means the final output is available.
        """
        return [
            ValidCompletedJob(job_id=cj.job_id, generator=cj.generator, params=cj.params, result_url=cj.result_url)
            for cj in self.get_completed_jobs()
            if cj.result_url is not None
        ]

    def await_completion(self, polling_interval: int = 10, timeout: Optional[int] = None) -> List[ValidCompletedJob]:
        """Serially poll and wait for all jobs in the batch to complete (blocking).

        **WARNING**: This function will hang forever if a backend error leads to a hung job
        (that never completes) and no timeout is set.

        Args:
            polling_interval: Time interval to sleep (in seconds) between consecutive iterations
                of polling. Defaults to 10 seconds.
            timeout: Optional timeout in seconds.

        Returns:
            :obj:`list` of all :obj:`CompletedJob`\s in batch.
        """
        num_jobs = len(self.jobs)
        if num_jobs == 0:
            return []
        start_time = datetime.now()
        num_jobs_remaining = self.num_jobs

        while num_jobs_remaining > 0:
            num_jobs_remaining = self.get_num_jobs_remaining()
            elapsed_time = int((datetime.now() - start_time).seconds)
            if timeout is not None:
                if elapsed_time > timeout:
                    raise TimeoutError(f"Batch completion time exceeded timeout of {timeout} seconds")
            print(f"\r{num_jobs_remaining} remaining jobs [{elapsed_time:d} s elapsed] ...", end=" ", flush=True)
            time.sleep(polling_interval)

        duration = datetime.now() - start_time
        print(f"Duration for all jobs: {duration.seconds} [s]")

        return self.get_valid_completed_jobs()

    def download(self, path: str, overwrite: bool = False) -> None:
        """Download completed jobs to a target folder.

        Args:
            path: Target path to download batch jobs to.
            overwrite: Flag for behavior if target path exists. If `True`, the target folder will
                be fully overwritten. If `False`, detected already downloaded jobs will not be
                re-downloaded.
        """
        out_dir = Path(path)
        batch_id_path = out_dir / "batch_id.txt"
        if not overwrite:
            if out_dir.exists():
                try:
                    with open(batch_id_path, "r") as f:
                        previous_id = f.read().strip()
                    if previous_id != self.batch_id:
                        raise DownloadError(
                            f"Attempt to download batch with id {self.batch_id} into existing folder for batch with id {previous_id}"
                        )
                except FileNotFoundError:
                    pass
                downloaded_jids = {e.stem for e in out_dir.iterdir() if e.is_dir()}
                downloadable_jobs = [j for j in self.get_valid_completed_jobs() if j.job_id not in downloaded_jids]
                print(f"Found {len(downloaded_jids)} jobs already downloaded")
            else:
                downloadable_jobs = self.get_valid_completed_jobs()
        else:
            downloadable_jobs = self.get_valid_completed_jobs()

        download_info = [(j.result_url, j.job_id, out_dir) for j in downloadable_jobs]
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(batch_id_path, "w") as f:
            f.write(f"{self.batch_id}")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_info = {executor.submit(_download_and_extract_zip, di): di for di in download_info}
            failed_jobs = []
            num_total_jobs = len(downloadable_jobs)
            num_jobs_completed = 0
            for future in concurrent.futures.as_completed(future_to_info.keys()):
                _, jid, out_path = future_to_info[future]
                try:
                    _ = future.result()
                except Exception:
                    if out_dir.exists():
                        try:
                            shutil.rmtree(out_path)
                        except Exception:
                            pass
                    failed_jobs.append(jid)
                else:
                    num_jobs_completed += 1
                    print(f"\rCompleted downloads: ({num_jobs_completed}/{num_total_jobs}) ...", end=" ", flush=True)

        if num_jobs_completed != num_total_jobs:
            # TODO: Consider truncating for huge numbs of jobs and immediate failure (no internet).
            raise DownloadError(
                f"{num_total_jobs - num_jobs_completed} jobs did not download successfully\nFailed job IDs: {failed_jobs}"
            )
        print("\nDownload complete!")


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
        A :obj:`Batch` instance from successful API submission.

    Raises:
        ValueError: If `token` or `generator` is empty.
        HTTPError: If batch submission post fails.
        BatchJobTypeError: If an unsupported job type is used.
    """
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
    return Batch(token=token, batch_id=batch_id, name=name, jobs=jobs, server=server, job_type=job_type)
