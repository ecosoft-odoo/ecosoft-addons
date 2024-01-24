To initiate API execution with job queue processing,
include the parameter "run_job_queue" set to 1 in your request.
Here's an example:

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "run_job_queue": 1,
            "vals": {
                  "payload": {
                     "field1": "value1",
                     ...
                  }
            }
         }
      }
