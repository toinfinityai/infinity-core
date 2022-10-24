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

Using a `Session` (Basic)
*************************

.. code-block:: python

    from infinity_api.session import Session

    # Start a session.
    token = "TOKEN"
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    
    # There is 1 way to generate synthetic data: submit a batch.
    # A single preview or job is just a batch with one element.
    single_preview = sesh.submit_to_api(job_params=[{"image_width": 512, "image_height": 512}], preview=True)
    single_video = sesh.submit_to_api(job_params=[{"num_reps": 1}])
    three_videos = sesh.submit_to_api(
        # Notice this is a list of three job param dictionaries.
        job_params=[{"camera_height": 1.0}, {"camera_height": 1.5}, {"camera_height": 2.0}]
    )

    # Wait for all the submitted synthetic data batches to complete.
    for batch in [single_preview, single_video, three_videos]:
        batch.await_jobs()
    # Or you can use this: sesh.await_all()
    
    # Download the results.
    single_preview.download(path="tmp/single_preview")
    single_video.download(path="tmp/single_video")
    three_videos.download(path="tmp/camera_height_batch")
    # Or you can use this: sesh.download_all("tmp/all_sesh_batches")
    
Using a `Session` (Advanced)
****************************

.. code-block:: python

    from infinity_api.session import Session

    # Start a session.
    token = "TOKEN"
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    
    # Create a batch with specific properties.
    import numpy as np
    job_params = []
    for _ in range(100):
        job_params.append({
            "scene": np.random.choice(["BEDROOM_2", "BEDROOM_4"]),
            "exercise": "UPPERCUT-RIGHT",
            "gender": np.random.choice(["MALE", "FEMALE"]),
            "num_reps": 5,
            "camera_height": np.random.uniform(1.0, 2.5),
            "relative_height": truncnorm(2.0, 1.0, -4.0, 4.0), # Custom truncated Normal
            "image_width": 256,
            "image_height": 256,
        })
        
    # Analyze job params before submission using `pandas` DataFrames.
    from pandas import DataFrame
    df = DataFrame.from_records(job_params)
    df.head()
    # Analyze/filter/modify/update ...
    job_params_final = df.to_dict("records")
    
    # Submit to generate synthetic data.
    previews_batch = sesh.submit_to_api(job_params=job_params, preview=True)
    print(batch.uid) # Print the batch ID.
    batch.await_jobs()
    batch.download(path="tmp/uppercut_right_custom1_previews")
    
    # Next week... come back and pick up where you left off.
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    # Provide batch ID (from local history/notes or by querying the API).
    old_uppercut_batch = sesh.batch_from_api(batch_id="BATCH_ID")
    # Review the jobs with a DF UX.
    df = DataFrame.from_records(old_uppercut_batch.jobs)
    # Filter/modify/etc.
    filtered_job_params = df.to_dict("records")
    # Submit an updated batch.
    videos_batch = sesh.submit_to_api(job_params=filtered_job_params, preview=False)
    videos_batch.await_jobs()
    videos_batch.download(path="tmp/uppercut_right_custom1_videos")
    
Using a `Session` (API Utilities)
*********************************

.. code-block:: python

    from pprint import pprint
    from infinity_api.session import Session

    # Start a session.
    token = "TOKEN"
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    
    # Print complete parameter information for the generator.
    # I.e., this will display parameter names and related metadata such as the
    # default value and constraints (min, max, set).
    pprint(sesh.parameter_info)

    # Query usage stats for the last month. This will break down your token's
    # usage stats as the number of samples rendered per unique generator.
    usage_stats = sesh.query_usage_last_n_days(30)
    pprint(usage_stats)
    
    # Query specific batches from the last month. This will return a list of
    # the batches you have submitted over the last month. You can view, analyze,
    # and use as a basis for another submission.
    batches_last_month = sesh.get_batches_last_n_days(30)
    pprint(batches_last_month)
    overrides = {"image_height": 512, "image_width": 512}
    new_batch = sesh.rerun_batch(batch=batches_last_month[2], overrides=overrides, preview=False)
    new_batch.await_jobs()
    new_batch.download(path="higher_res_batch")
    
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
