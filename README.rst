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

    # Start a session with the Infinity API.
    token = "TOKEN"
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    
    # Submit a request for three synthetic data videos.
    job_params = [{"camera_height": v} for v in [1.0, 1.5, 2.0]]
    videos = sesh.submit(job_params=job_params)
    
    # Manually check if they are done yet.
    print(f"Completed yet? Answer: {videos.num_remaining_jobs == 0)})
    
    # Manually block until they are all done.
    videos.await_completion()
    
    # Download the results.
    videos.download(path="tmp/three_camera_height_sweep_videos")
    
Using a `Session` (Advanced)
****************************

.. code-block:: python

    from infinity_api.session import Session

    # Start a session.
    token = "TOKEN"
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    
    # Create a big batch with specific properties.
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
    # ... do stuff like filter/modify/add to the dataframe ...
    job_params_final = df.to_dict("records")
    # You can manually check/validate your job params before trying to submit:
    try:
        sesh.validate(job_params=job_params_final)
    except ValidationError as e:
        print("Validation errors: {e}")
    
    # Submit to generate synthetic data.
    previews_batch = sesh.submit(name="app1", job_params=job_params_final, preview=True)
    print(f"Submitted batch ID: {batch.uid}) # Print the batch ID.
    batch.await_completion()
    batch.download(path="tmp/uppercut_right_custom1_previews")
    
    # Next week... come back and pick up where you left off:
    sesh = Session(token=token, name="demo", generator="visionfit-v0.3.1")
    # Provide batch ID (from local history/notes or by querying the API).
    old_uppercut_batch = sesh.batch_from_api(batch_id="UPPERCUT_BATCH_ID")
    # Review the jobs with a `DataFrame` UX.
    df_uppercut = DataFrame.from_records(old_uppercut_batch.job_params)
    # ... do stuff like filter/modify/add to the dataframe ...
    updated_job_params = df_uppercut.to_dict("records")
    # Grab another batch:
    old_pushup_batch = sesh.batch_from_api(batch_id="PUSHUP_BATCH_ID")
    df_pushup = DataFrame.from_records(old_pushup_batch.job_params)
    # ... do stuff like filter/modify/add to the dataframe ...
    # Merge the updated uppercut and pushup jobs into a single list of jobs.
    merged_df = pandas.concat([df_uppercut, df_pushup])
    final_job_params = merged_df.to_dict("records")

    # Submit the updated and combined new batch.
    videos_batch = sesh.submit(name="frankenstein", job_params=final_job_params, preview=False)
    videos_batch.await_completion()
    videos_batch.download(path="tmp/updated_and_merged_rerun")
    
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
    usage_stats = sesh.get_usage_stats_last_n_days(30)
    pprint(usage_stats)
    
    # Query specific batches from the last month. This will return a list of
    # the batches you have submitted over the last month. You can view, analyze,
    # and use as a basis for another submission.
    batches_last_month = sesh.get_batches_last_n_days(30)
    for name, batch_id in batches_last_month:
        print(f"{name} ({batch_id}))
    
    # Target the third batch for a rerun.
    _name, batch_id = batches_last_month[2]
    third_batch = sesh.batch_from_api(batch_id=batch_id)
    job_params = third_batch.job_params
    for jp in job_params:
        jp["image_width": 512]
        jp["image_height": 512]
    
    third_batch_higher_res = sesh.submit(name="higher res", job_params=job_params)
    third_batch_higher_res.await_completion()
    third_batch.download(path="higher_res_batch")

Using the `api` module directly
*******************************

.. code-block:: python

    from infinity_api import api

    token = "MY_TOKEN" # Your authentication token from Infinity AI.

    # Get parameter information for a specific VisionFit generator.
    visionfit_info = api.get_single_generator_data(token=token, generator_name="visionfit-v0.3.1")
    print(visionfit_info)

    # Get your usage from the last 30 days.
    usage_stats = api.get_usage_last_n_days(token=token, n_days=30)
    print(usage_stats)

    # Post a request for a single preview using default parameters.
    r = api.post_batch(
        token=token,
        generator="visionfit",
        name="single preview",
        job_params=[{}],
        is_preview=True,
        server=api.DEFAULT_SERVER
    )
    assert r.ok

    # Post a request for three standard video jobs using default parameters.
    r = api.post_batch(
        token=token,
        generator="visionfit",
        name="three default jobs",
        job_params=[{}, {}, {}],
        is_preview=False,
        server=api.DEFAULT_SERVER
    )
    assert r.ok
