from urllib.parse import urlencode
from datetime import datetime, timedelta
from typing import Any, Optional

import requests


DEFAULT_SERVER: str = "https://api.toinfinity.ai"


def get_all_preview_data():
    pass


def get_single_preview_data():
    pass


def get_all_job_data():
    pass


def get_single_job_data():
    pass


def get_all_generator_data():
    pass


def get_single_generator_data():
    pass


def get_openapi_schema():
    pass


def get_usage_datetime_range(
    token: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    server: str = DEFAULT_SERVER,
) -> Dict[str, Any]:

    if end_time is not None and start_time is not None:
        if end_time < start_time:
            raise ValueError(f"End time ({end_time}) before start time ({start_time}) for usage query")

    query_dict = dict()
    if start_time is not None:
        if start_time.tzinfo is None:
            start_time = start_time.astimezone()
        query_dict["start_time"] = start_time.isoformat()
    if end_time is not None:
        if end_time.tzinfo is None:
            end_time = end_time.astimezone()
        query_dict["end_time"] = end_time.isoformat()

    query_url = server + "/api/job_runs/counts/" + "?" + urlencode(query_dict)

    r = requests.get(
        query_url,
        headers={"Authorization": f"Token {token}"},
    )

    if r.status_code == 200:
        return r.json()
    else:
        raise ValueError(f"Error querying usage stats (status code {r.status_code}), details: {r.json()['detail']}")


def get_usage_last_n_days(
    token: str,
    n_days: int,
    server: str = DEFAULT_SERVER,
) -> Dict[str, Any]:
    end_time = datetime.now().astimezone()
    start_time = end_time - timedelta(days=n_days)
    return get_usage_datetime_range(token=token, server=server, start_time=start_time, end_time=end_time)


def post_preview():
    pass


def post_job():
    pass
