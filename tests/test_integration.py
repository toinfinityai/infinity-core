from pathlib import Path

import pytest

import infinity_core.api as api


def _construct_config_file(filename: str) -> Path:
    return Path(__file__).parent.absolute() / filename


def _read_string_from_file(filepath: Path) -> str:
    with open(filepath, "r") as f:
        return f.read().strip()


@pytest.fixture
def server() -> str:
    return _read_string_from_file(_construct_config_file("server.txt"))


@pytest.fixture
def token() -> str:
    return _read_string_from_file(_construct_config_file("token.txt"))


@pytest.fixture
def preview_job_id() -> str:
    return _read_string_from_file(_construct_config_file("preview_job_id.txt"))


@pytest.fixture
def preview_batch_id() -> str:
    return _read_string_from_file(_construct_config_file("preview_batch_id.txt"))


@pytest.fixture
def standard_job_id() -> str:
    return _read_string_from_file(_construct_config_file("standard_job_id.txt"))


@pytest.fixture
def standard_batch_id() -> str:
    return _read_string_from_file(_construct_config_file("standard_batch_id.txt"))


@pytest.fixture
def generator_name() -> str:
    return _read_string_from_file(_construct_config_file("generator_name.txt"))


@pytest.mark.integration
@pytest.mark.apiget
class TestApiGetRequestIntegration:
    def test_get_all_preview_job_data(self, token: str, server: str) -> None:
        r = api.get_all_preview_job_data(token=token, server=server)

        assert r.ok

    def test_get_single_preview_job_data(self, token: str, preview_job_id: str, server: str) -> None:
        r = api.get_single_preview_job_data(token=token, preview_id=preview_job_id, server=server)

        assert r.ok

    def test_get_batch_preview_job_data(self, token: str, preview_batch_id: str, server: str) -> None:
        r = api.get_batch_data(token=token, batch_id=preview_batch_id, server=server)

        assert r.ok

    def test_get_all_standard_data(self, token: str, server: str) -> None:
        r = api.get_all_standard_job_data(token=token, server=server)

        assert r.ok

    def test_get_single_standard_job_data(self, token: str, standard_job_id: str, server: str) -> None:
        r = api.get_single_standard_job_data(token=token, standard_job_id=standard_job_id, server=server)

        assert r.ok

    def test_get_batch_standard_job_data(self, token: str, standard_batch_id: str, server: str) -> None:
        r = api.get_batch_data(token=token, batch_id=standard_batch_id, server=server)

        assert r.ok

    def test_get_all_generator_data(self, token: str, server: str) -> None:
        r = api.get_all_generator_data(token=token, server=server)

        assert r.ok

    def test_get_single_generator_data(self, token: str, generator_name: str, server: str) -> None:
        r = api.get_single_generator_data(token=token, generator_name=generator_name, server=server)

        assert r.ok

    def test_get_openapi_schema(self, token: str, server: str) -> None:
        r = api.get_openapi_schema(token=token, server=server)

        assert r.ok

    def test_get_usage_datetime_range(self, token: str, server: str) -> None:
        r = api.get_usage_datetime_range(token=token, server=server)

        assert r.ok

    def test_get_usage_last_n_days(self, token: str, server: str) -> None:
        r = api.get_usage_last_n_days(token=token, n_days=30, server=server)

        assert r.ok


@pytest.mark.integration
@pytest.mark.apipost
class TestApiPostRequestIntegration:
    def test_post_batch_preview(self, token: str, generator_name: str, server: str) -> None:
        r = api.post_batch(
            token=token, generator=generator_name, name="test", job_params=[{}], is_preview=True, server=server
        )

        assert r.ok

    def test_post_batch_standard(self, token: str, generator_name: str, server: str) -> None:
        r = api.post_batch(
            token=token, generator=generator_name, name="test", job_params=[{}], is_preview=False, server=server
        )

        assert r.ok

    def test_post_multi_job_batch(self, token: str, generator_name: str, server: str) -> None:
        r = api.post_batch(
            token=token, generator=generator_name, name="test", job_params=[{}, {}], is_preview=True, server=server
        )

        assert r.ok


# @pytest.mark.integration
# @pytest.mark.batchpost
# class TestBatchSubmissionIntegration:
#     def test_preview_batch(self, token: str, generator_name: str, server: str) -> None:
#         batch, _ = ba.submit_batch_to_api(
#             token=token,
#             generator=generator_name,
#             job_type=JobType.PREVIEW,
#             job_params=[dict()],
#             output_dir="tmp",
#             server=server,
#             write_to_file=False,
#         )

#         assert batch.num_successfully_submitted_jobs == 1

#     def test_standard_batch(self, token: str, generator_name: str, server: str) -> None:
#         batch, _ = ba.submit_batch_to_api(
#             token=token,
#             generator=generator_name,
#             job_type=JobType.STANDARD,
#             job_params=[dict()],
#             output_dir="tmp",
#             server=server,
#             write_to_file=False,
#         )

#         assert batch.num_successfully_submitted_jobs == 1
