import pytest

import infinity_api.api as api
from infinity_api.data_structures import HeaderKind


class TestBuildRequest:
    def test_reject_empty_token_string(self):
        token = ""
        with pytest.raises(ValueError):
            api.build_request(token=token, server=api.DEFAULT_SERVER, endpoint="ep")

    def test_reject_empty_server(self):
        server = ""
        with pytest.raises(ValueError):
            api.build_request(token="123", server=server, endpoint="ep")

    def test_reject_empty_endpoint(self):
        endpoint = ""
        with pytest.raises(ValueError):
            api.build_request(token="123", server=api.DEFAULT_SERVER, endpoint=endpoint)

    @pytest.mark.parametrize("endpoint", ["api/ep", "/api/ep", "/api/ep/", "api/ep/"])
    def test_join_server_and_endpoint(self, endpoint):
        token = "123"
        server = "https://api.company.com"
        url, _ = api.build_request(token=token, server=server, endpoint=endpoint)

        assert url == server + "/api/ep/"

    def test_join_query_paremeters(self):
        token = "123"
        server = api.DEFAULT_SERVER
        endpoint = "ep"
        query_parameters = {"var1": 1, "var2": 2}
        url, _ = api.build_request(token=token, server=server, endpoint=endpoint, query_parameters=query_parameters)

        assert url == server + "/ep/" + "?" + "var1=1&var2=2/"

    def test_combined_headers(self):
        token = "123"
        server = api.DEFAULT_SERVER
        endpoint = "ep"
        headers_set = set([HeaderKind.AUTH, HeaderKind.ACCEPT_JSON, HeaderKind.JSON_CONTENT])
        _, headers = api.build_request(token=token, server=server, endpoint=endpoint, headers=headers_set)

        exp_headers = {
            **HeaderKind.AUTH.to_header_dict(token),
            **HeaderKind.ACCEPT_JSON.to_header_dict(token),
            **HeaderKind.JSON_CONTENT.to_header_dict(token),
        }

        assert headers == exp_headers
