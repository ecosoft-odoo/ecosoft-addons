To enable job queue processing during API execution,
include the `queue_job` parameter in your request payload.

The request payload should follow this structure:

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "payload": {
                  // Your payload data here
               },
               "queue_job": {
                  "run_queue": True,  # Enable job queue processing
                  "channel": "<channel name>",  # Optional, defaults to "root.webhook_api"
               }
            }
         }
      }

Upon successfully calling the API with job queue processing, the response will look like this:

  .. code-block:: python

      {
         "jsonrpc": "2.0",
         "id": null,
         "result": {
            "is_success": true,
            "job_uuid": "3b9ab72f-3503-4151-972d-c160622cff3d",
            "channel": "<channel name>",  # Channel used for the job
            "result": {},
            "messages": "Record run job queue successfully"
         }
      }

Notes:
- If the `channel` parameter is not specified, the default channel will be `root.webhook_api`.
- The API response will include a job UUID to track the processing.
