from typing import List, Dict
import urllib
import zipfile
from pathlib import Path

import requests

from infinity_api.data_structures import CompletedJob


def download_completed_jobs(completed_jobs: List[CompletedJob], output_dir: str) -> List[str]:
    """Downloads completed jobs to output directory.

    Returns:
        List of folders corresponding to each completed job.
    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True)
    job_folders = []
    print("Downloading completed jobs...")
    for job in completed_jobs:
        zip_file = output_dir_path / job.job_id / ".zip"
        if job.result_url is None:
            continue
        urllib.request.urlretrieve(job.result_url, zip_file)
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(output_dir)
        Path(zip_file).unlink()
        job_folders.append(output_dir_path / job.job_id)

    return job_folders


def job_ids_from_completed_jobs(completed_jobs: List[CompletedJob]) -> List[str]:
    """Returns job ids from a list of completed jobs."""
    return [cj.job_id for cj in completed_jobs]


def filter_for_valid_ids(completed_jobs: List[CompletedJob]) -> List[str]:
    """Returns valid job ids (result URL) from a list of completed jobs."""
    return [cj.job_id for cj in completed_jobs if cj.result_url]


def fetch_params_by_id(
    server: str,
    endpoint: str,
    token: str,
    job_id: str,
) -> Dict:
    """Returns parameters corresponding to specific job id."""

    r = requests.get(
        f"{server}{endpoint}{job_id}/",
        headers={"Authorization": f"Token {token}"},
    )
    return r.json()["param_values"]
