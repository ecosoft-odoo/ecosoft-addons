Extends ``zort_connector`` to process order synchronization and pending-order
conversion **asynchronously via queue jobs** (using ``queue_job_cron``).

By default, ``zort_connector`` fetches and processes all Zort order pages
synchronously inside the cron transaction. For stores with a large number of
orders this can cause long-running transactions and cron timeouts. This module
offloads the heavy work to the OCA queue-job runner so each page is processed
in its own independent job.

**What it adds**

- **Async page dispatch** - overrides ``_dispatch_sync_page`` so that each
  page of a Zort order sync run is enqueued as a separate queue job
  (description: *"Zort sync page N/total"*).
- **Async pending-order batches** - overrides ``_dispatch_pending_orders_batch``
  so that each batch of pending ``zort.order`` records is enqueued as a
  separate queue job.
- **Cron flag** - sets ``run_as_queue_job = True`` and
  ``no_parallel_queue_job_run = True`` on the base **Auto Sync Zort Order**
  cron, so the scheduler dispatches a queue job instead of running inline and
  prevents duplicate concurrent runs.
- **Graceful fallback** - both dispatch overrides detect whether they are
  already running inside a queue job (via ``job_uuid`` in context). If not,
  they fall back to synchronous base behaviour, so the module is safe to
  install even when the queue runner is temporarily stopped.
