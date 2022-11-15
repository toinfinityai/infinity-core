from typing import Any, Dict, List

import pytest

import infinity_core.api as api
from infinity_core.session import Session


@pytest.fixture
def session() -> Session:
    sesh = object.__new__(Session)
    sesh.token = "test-token"
    sesh.generator = "visionfit"
    sesh.server = api.DEFAULT_SERVER
    sesh.batches = []
    sesh._generator_info = {
        "name": "test-generator-v0.1.0",
        "version": "0.1.0",
        "params": [
            {
                "name": "param1",
                "type": "int",
                "default_value": 1,
                "options": {
                    "min": 1,
                    "max": 5,
                },
            },
            {"name": "param2", "type": "float", "default_value": 2.5, "options": {"min": -5.0, "max": 5.0}},
            {
                "name": "param3",
                "type": "str",
                "default_value": "CHOICE_1",
                "options": {"choices": ["CHOICE_1", "CHOICE_2"]},
            },
        ],
        "options": {
            "preview": True,
        },
    }

    return sesh


class TestSessionJobParamValidation:
    def test_valid_job_params(self, session: Session) -> None:
        job_params: List[Dict[str, Any]] = [{"param1": 2}, {"param2": 1.2}, {"param3": "CHOICE_2"}]
        assert all([v is None for v in session.validate_job_params(job_params=job_params)])

    def test_invalid_type(self, session: Session) -> None:
        job_params: List[Dict[str, Any]] = [{"param1": "2"}, {"param2": 2}]
        errors = session.validate_job_params(job_params=job_params)
        assert all([e is not None for e in errors])

    def test_invalid_parameter(self, session: Session) -> None:
        job_params: List[Dict[str, Any]] = [{"param4": 1.5}]
        errors = session.validate_job_params(job_params=job_params)
        assert errors[0] is not None

    def test_out_of_range_parameter(self, session: Session) -> None:
        job_params: List[Dict[str, Any]] = [{"param1": 10}, {"param2": -100.0}]
        errors = session.validate_job_params(job_params=job_params)
        assert all([e is not None for e in errors])

    def test_out_of_choice_set(self, session: Session) -> None:
        job_params = [{"param3": "CHOICE_3"}]
        errors = session.validate_job_params(job_params=job_params)
        assert errors[0] is not None
