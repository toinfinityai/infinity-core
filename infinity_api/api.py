from functools import reduce
from operator import ior
from urllib.parse import urlencode, urljoin
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Tuple, Set

import requests

from infinity_api.data_structures import HeaderKind


DEFAULT_SERVER: str = "https://api.toinfinity.ai"


def _ensure_trailing_slash(url: str) -> str:
    url if url.endswith("/") else url + "/"


def build_get_request(
    token: str, server: str, endpoint: str, headers: Set[HeaderKind], query_parameters: Optional[Dict[str, str]] = None
) -> Tuple[str, Dict[str, str]]:
    url = urljoin(server, endpoint)
    url = _ensure_trailing_slash(url)
    if query_parameters:
        url += "?" + urlencode(query_parameters)
        url = _ensure_trailing_slash(url)
    headers = reduce(ior, [h.to_header_dict(token) for h in headers], dict())

    return url, headers


def get_all_preview_data(token: str, server: str = DEFAULT_SERVER):
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint="api/job_previews/",
        headers=set(HeaderKind.AUTH, HeaderKind.ACCEPT_JSON),
    )
    return requests.get(url=url, headers=headers)


def get_single_preview_data(token: str, preview_id: str, server: str = DEFAULT_SERVER):
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint=f"api/job_previews/{preview_id}/",
        headers=set(HeaderKind.AUTH, HeaderKind.ACCEPT_JSON),
    )
    return requests.get(url=url, headers=headers)


def get_all_standard_job_data(token: str, server: str = DEFAULT_SERVER):
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint=f"api/job_runs/",
        headers=set(HeaderKind.AUTH, HeaderKind.ACCEPT_JSON),
    )
    return requests.get(url=url, headers=headers)


def get_single_standard_job_data(token: str, standard_job_id: str, server: str = DEFAULT_SERVER):
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint=f"api/job_runs/{standard_job_id}/",
        headers=set(HeaderKind.AUTH, HeaderKind.ACCEPT_JSON),
    )
    return requests.get(url=url, headers=headers)


def get_all_generator_data(token: str, server: str = DEFAULT_SERVER):
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint=f"api/jobs/",
        headers=set(HeaderKind.AUTH, HeaderKind.ACCEPT_JSON),
    )
    return requests.get(url=url, headers=headers)


def get_single_generator_data(token: str, generator_name: str, server: str = DEFAULT_SERVER):
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint=f"api/jobs/{generator_name}/",
        headers=set(HeaderKind.AUTH, HeaderKind.ACCEPT_JSON),
    )
    return requests.get(url=url, headers=headers)


def get_openapi_schema(token: str, format: str = "yaml", language: str = "en", server: str = DEFAULT_SERVER):
    headers = {HeaderKind.AUTH}
    query_parameters = dict()
    if format == "yaml":
        headers.add(HeaderKind.ACCEPT_OPENAPI_YAML)
        query_parameters["format"] = format
    elif format == "json":
        headers.add(HeaderKind.ACCEPT_OPENAPI_JSON)
        query_parameters["format"] = format
    else:
        raise ValueError(f"Unsupported OpenAPI schema format: `{format}` must be `yaml` or `json`")
    query_parameters["lang"] = language
    url, headers = build_get_request(
        token=token,
        server=server,
        endpoint=f"api/schema/",
        headers=headers,
        query_parameters=query_parameters,
    )
    return requests.get(url=url, headers=headers)


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
