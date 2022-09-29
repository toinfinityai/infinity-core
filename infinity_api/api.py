from functools import reduce
from operator import ior
from urllib.parse import urlencode, urljoin
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Tuple, Set, List, Union

import requests
from requests.models import Response

from infinity_api.data_structures import HeaderKind


DEFAULT_SERVER: str = "https://api.toinfinity.ai"


def _ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def build_request(
    token: str, server: str, endpoint: str, headers: Optional[Set[HeaderKind]] = None, query_parameters: Optional[Dict[str, str]] = None
) -> Tuple[str, Dict[str, str]]:
    if token == "":
        raise ValueError("`token` cannot be an empty string")
    if server == "":
        raise ValueError("`server` cannot be an empty string")
    if endpoint == "":
        raise ValueError("`endpoint` cannot be an empty string")

    url = urljoin(server, endpoint)
    url = _ensure_trailing_slash(url)
    if query_parameters is not None:
        url += "?" + urlencode(query_parameters)
        url = _ensure_trailing_slash(url)
    if headers is not None:
        headers_dict: Dict[str, str] = reduce(ior, [h.to_header_dict(token) for h in headers], dict())
    else:
        headers_dict = dict()

    return url, headers_dict


def unwrap_raw_bytes_payload(response: Response) -> bytes:
    response.raise_for_status()
    return response.content


def unwrap_json_payload(response: Response) -> Dict[str, Any]:
    response.raise_for_status()
    return response.json()


def unwrap_text_payload(response: Response) -> str:
    response.raise_for_status()
    return response.text


def get_all_preview_data(token: str, server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/job_previews/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
    )
    return requests.get(url=url, headers=headers)


def get_single_preview_data(token: str, preview_id: str, server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint=f"api/job_previews/{preview_id}/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
    )
    return requests.get(url=url, headers=headers)


def get_batch_preview_data(token: str, batch_id: str, server: str = DEFAULT_SERVER) -> Response:
    headers_set = set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON])
    query_parameters = {"batch_id": batch_id}
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/job_previews/",
        headers=headers_set,
        query_parameters=query_parameters,
    )
    return requests.get(url=url, headers=headers)


def get_all_standard_job_data(token: str, server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/job_runs/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
    )
    return requests.get(url=url, headers=headers)


def get_single_standard_job_data(token: str, standard_job_id: str, server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint=f"api/job_runs/{standard_job_id}/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
    )
    return requests.get(url=url, headers=headers)


def get_batch_standard_job_data(token: str, batch_id: str, server: str = DEFAULT_SERVER) -> Response:
    headers_set = set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON])
    query_parameters = {"batch_id": batch_id}
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/job_runs/",
        headers=headers_set,
        query_parameters=query_parameters,
    )
    return requests.get(url=url, headers=headers)


def get_all_generator_data(token: str, server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/jobs/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
    )
    return requests.get(url=url, headers=headers)


def get_single_generator_data(token: str, generator_name: str, server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint=f"api/jobs/{generator_name}/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
    )
    return requests.get(url=url, headers=headers)


def get_openapi_schema(
    token: str, format: str = "yaml", language: str = "en", server: str = DEFAULT_SERVER
) -> Response:
    headers_set = {HeaderKind.AUTH}
    query_parameters = dict()
    if format == "yaml":
        headers_set.add(HeaderKind.ACCEPT_OPENAPI_YAML)
        query_parameters["format"] = format
    elif format == "json":
        headers_set.add(HeaderKind.ACCEPT_OPENAPI_JSON)
        query_parameters["format"] = format
    else:
        raise ValueError(f"Unsupported OpenAPI schema format: `{format}` must be `yaml` or `json`")
    query_parameters["lang"] = language
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/schema/",
        headers=headers_set,
        query_parameters=query_parameters,
    )
    return requests.get(url=url, headers=headers)


def get_usage_datetime_range(
    token: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    server: str = DEFAULT_SERVER,
) -> Response:
    if end_time is not None and start_time is not None:
        if end_time < start_time:
            raise ValueError(f"End time ({end_time}) before start time ({start_time}) for usage query")
    query_parameters = dict()
    if start_time is not None:
        if start_time.tzinfo is None:
            start_time = start_time.astimezone()
        query_parameters["start_time"] = start_time.isoformat()
    if end_time is not None:
        if end_time.tzinfo is None:
            end_time = end_time.astimezone()
        query_parameters["end_time"] = end_time.isoformat()
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/job_runs/counts/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON]),
        query_parameters=query_parameters,
    )
    return requests.get(url=url, headers=headers)


def get_usage_last_n_days(
    token: str,
    n_days: int,
    server: str = DEFAULT_SERVER,
) -> Response:
    end_time = datetime.now().astimezone()
    start_time = end_time - timedelta(days=n_days)
    return get_usage_datetime_range(token=token, server=server, start_time=start_time, end_time=end_time)


def post_preview(token: str, json_data: Dict[str, Any], server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/jobs/preview/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON, HeaderKind.JSON_CONTENT]),
    )
    return requests.post(url=url, headers=headers, json=json_data)


def post_standard_job(token: str, json_data: Dict[str, Any], server: str = DEFAULT_SERVER) -> Response:
    url, headers = build_request(
        token=token,
        server=server,
        endpoint="api/jobs/run/",
        headers=set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON, HeaderKind.JSON_CONTENT]),
    )
    return requests.post(url=url, headers=headers, json=json_data)
