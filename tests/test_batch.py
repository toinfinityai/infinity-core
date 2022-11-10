# from datetime import datetime

# import pytest

# import infinity_core.api as api
# import infinity_core.batch as ba
# from infinity_core.data_structures import FailedJobRequest, JobType, SuccessfulJobRequest


# @pytest.fixture
# def batch() -> ba.Batch:
#     return ba.Batch(
#         uid="123456789",
#         timestamp=datetime(2022, 10, 9, 21, 41, 31, 376152).strftime("%Y%m%d_T%H%M%S%f"),
#         folder_suffix=None,
#         jobs=[SuccessfulJobRequest(job_id="1", params=dict())],
#         failed_requests=[FailedJobRequest(status_code=500, params=dict())],
#         generator="visionfit",
#         server=api.DEFAULT_SERVER,
#         job_type=JobType.PREVIEW,
#         output_dir="tmp",
#         token="test",
#     )


# class TestBatch:
#     def test_job_ids_property(self, batch: ba.Batch) -> None:
#         assert batch.job_ids == ["1"]

#     def test_correct_num_successful_jobs(self, batch: ba.Batch) -> None:
#         assert batch.num_successfully_submitted_jobs == 1

#     def test_correct_num_failed_jobs(self, batch: ba.Batch) -> None:
#         assert batch.num_failed_job_submissions == 1

#     def test_serde_inverse(self, batch: ba.Batch) -> None:
#         batch_json_str = batch.to_json()
#         reconstituted_batch = ba.Batch.from_json(json_str=batch_json_str, token=batch.token)
#         assert reconstituted_batch == batch


# class TestSubmitBatch:
#     def test_reject_empty_string_token(self) -> None:
#         token = ""
#         with pytest.raises(ValueError):
#             ba.submit_batch_to_api(
#                 token=token,
#                 generator="visionfit",
#                 job_type=JobType.PREVIEW,
#                 job_params=list(),
#                 output_dir="tmp",
#             )

#     def test_reject_empty_string_generator(self) -> None:
#         generator = ""
#         with pytest.raises(ValueError):
#             ba.submit_batch_to_api(
#                 token="test",
#                 generator=generator,
#                 job_type=JobType.PREVIEW,
#                 job_params=list(),
#                 output_dir="tmp",
#             )
