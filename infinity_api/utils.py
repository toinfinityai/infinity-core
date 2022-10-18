import urllib
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import infinity_api.api as api
from infinity_api.data_structures import CompletedJob, JobType


def download_completed_jobs(completed_jobs: List[CompletedJob], output_dir: str) -> List[Path]:
    """Downloads completed jobs to output directory.

    Returns:
        List of folders corresponding to each completed job.
    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True)
    job_folders = []
    print("Downloading completed jobs...")
    for job in completed_jobs:
        zip_file = output_dir_path / job.uid / ".zip"
        if job.result_url is None:
            continue
        urllib.request.urlretrieve(job.result_url, zip_file)
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(output_dir)
        Path(zip_file).unlink()
        job_folders.append(output_dir_path / job.uid)

    return job_folders


def job_ids_from_completed_jobs(completed_jobs: List[CompletedJob]) -> List[str]:
    """Returns job ids from a list of completed jobs."""
    return [cj.uid for cj in completed_jobs]


def filter_for_valid_ids(completed_jobs: List[CompletedJob]) -> List[str]:
    """Returns valid job ids (result URL) from a list of completed jobs."""
    return [cj.uid for cj in completed_jobs if cj.result_url]


def fetch_params_by_id(
    token: str,
    job_type: JobType,
    job_id: str,
    server: str = api.DEFAULT_SERVER,
) -> Any:
    """Returns parameters corresponding to specific job id."""

    if job_type == JobType.PREVIEW:
        r = api.get_single_preview_job_data(token=token, preview_id=job_id, server=server)
    elif job_type == JobType.STANDARD:
        r = api.get_single_standard_job_data(token=token, standard_job_id=job_id, server=server)
    else:
        raise ValueError(f"Unsupported job type `{job_type}` for fetching job parameters")

    r.raise_for_status()
    return r.json()["param_values"]
