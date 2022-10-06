Module Summaries
================

api
---

This module provides lightweight Python wrapping of the Infinity AI API for synthetic data generation. Use this module to directly interact with the Infinity API or to build higher level abstractions for interfacing with the Infinity API. For example, the `batch` module provides a higher level abstraction for batches of synthetic data and uses this module to interact directly with the REST API.

.. image:: https://static1.smartbear.co/swagger/media/assets/images/swagger_logo.svg
    :target: https://api.toinfinity.ai/api/schema/swagger-ui/
    :width: 250

A `Swagger UI is available <https://api.toinfinity.ai/api/schema/swagger-ui/>`_ for the Infinity API. The `OpenAPI <https://www.openapis.org/>`_ schema can also be obtained through the `api` module:

.. code-block:: python

    import infinity_api.api

    schema = api.unwrap_text_payload(api.get_openapi_schema(token="MY_TOKEN"))
    print(schema)

This documents our OpenAPI The Swagger UI provides a web-based interface to perform low-level interactions with the REST endpoint through the browser. A valid authentication token is required.

Basic Usage
***********

.. code-block:: python
    
    from infinity_api import api as api

    my_token = "MY_TOKEN"
    api.get_all_generator_data(my_token)

    r = api.post_standard_job(token=token, json_data={"name": "visionfit", "param_values": {}})
    print(r.status_code)

batch
-----

This module provides data structures and associated functionality to abstract over the concept of batch submission/generation for Infinity synthetic data. Use this module's abstractions to generate, track, and manipulate batches of synthetic data.

This module is built around the `Batch` data structure. Key features of a `Batch`:

- A single free function to submit a batch to the API and return a corresponding `Batch` instance.
- Seamless serializationn/deserialization to JSON string/file on disk. This can be used to reconstitute an old batch at any time and query the API for batch-specific information.
- Convenience methods to await all job completion, query for completed jobs, and disambiguate between valid/invalid completed jobs.

Basic Usage
***********

.. code-block:: python

    from infinity_api.batch import Batch, submit_batch_to_api

    def make_interesting_param_distribution(generator: str = "visionfit") -> Dict[str, Any]:
        # TODO: Construct a list of job parameters, sweeping and/or modifying parameters as desired.
        return dict()

    my_token = "MY_TOKEN"

    generator = "visionfit"
    batch = submit_batch_to_api(
        token=token,
        generator=generator,
        job_type = JobType.STANDARD,
        job_params = make_interesting_param_distribution(generator),
        batch_folder_suffix="large_batch",
        output_dir="tmp",
    )
    completed_jobs = batch.await_jobs()
    print(completed_jobs)

data_structures
---------------

This module contains common or important data structures used in other `infinity-api` modules.
