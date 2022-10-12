.. image:: docs/source/infinity_ai_logo.png
    :width: 200
    :alt: Infinity AI, Inc.

Infinity API
############

.. image:: https://github.com/toinfinityai/infinity-api-dev/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/toinfinityai/infinity-api-dev/actions/workflows/python-package.yml

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: http://www.mypy-lang.org/static/mypy_badge.svg
    :target: http://mypy-lang.org

.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://pycqa.github.io/isort/

The **infinity_api** package provides tools to interact with the `Infinity API <https://infinity.ai>`_ and generate synthetic data.

Requirements
------------

The **infinity_api** package requires Python 3.7 or newer.

Installation
------------

Add to a Python project with Poetry:

.. code-block:: text

    poetry add infinity_api

Install from PyPI:

.. code-block:: text

    pip install infinity_api

Install from the source located on GitHub:

.. code-block:: text
    
    git clone git@github.com:toinfinityai/infinity-api-dev.git
    poetry install

Examples
--------

Using a `Session`
*****************

.. code-block:: python

    from infinity_api.session import Session
    token = "TOKEN"

    sesh = Session(name="demo", generator="visionfit-v0.3.1", token=token)

    # Print parameter information for the generator.
    print(sesh.parameters)

    # Post a single job with all default parameters.
    single_preview = sesh.submit_preview_batch(job_params=[])

    # Post a single job with all default parameters.
    single_job = sesh.submit_standard_batch(job_params=[])

Using the `api` module directly
*******************************

.. code-block:: python

    from infinity_api import api

    my_token = "MY_TOKEN" # Your authentication token from Infinity AI.

    # Get parameter information for a specific VisionFit generator.
    visionfit_info = api.get_single_generator_data(token=token, generator_name="visionfit-v0.3.1")
    print(visionfit_info)

    # Get your usage from the last 30 days.
    usage_stats = api.get_usage_last_n_days(token=token, n_days=30)
    print(usage_stats)

    # Post a request for a single preview using default parameters.
    json_for_default = {"name": "visionfit", "param_values": {}}
    r = api.post_preview(token=token, json_data=json_for_default)
    assert r.ok

    # Post a request for a single standard video job using default parameters.
    r = api.post_standard_job(token=token, json_data=json_for_default)
    assert r.ok

Using the `batch` module directly
*********************************

.. code-block:: python

    # Submit a batch of two previews and await the results.
    from infinity_api import batch
    from infinity_api.data_structures import JobType

    small_batch = batch.submit_batch_to_api(
        token=token,
        generator="visionfit",
        job_type=JobType.PREVIEW,
        job_params=[json_for_default, json_for_default],
        batch_folder_suffix="example_batch",
        output_dir="tmp",
    )
    completed_jobs = small_batch.await_jobs()
    print(completed_jobs)
