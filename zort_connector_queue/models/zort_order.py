# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ZortOrder(models.Model):
    _inherit = "zort.order"

    def _is_running_as_queue_job(self):
        """Return True when the current execution context is a queue job.

        ``queue_job_cron`` dispatches a cron as a queue job when the cron's
        ``run_as_queue_job`` flag is enabled.  The queue-job runner always injects
        ``job_uuid`` into the environment context, so this key being present means
        we are already inside a job and should dispatch sub-work as jobs too.
        """
        return bool(self.env.context.get("job_uuid"))

    @api.model
    def _dispatch_sync_page(
        self,
        sync_log_id,
        page,
        total_pages,
        base_payload,
        sync_to_str,
        page_result,
        is_last_page,
    ):
        """Dispatch as a queue job only when called from a queue job.

        If the ir.cron that triggered this run has ``run_as_queue_job`` enabled,
        ``job_uuid`` is present in context and each page becomes an async job.
        Otherwise falls back to synchronous execution (base behaviour).
        """
        if not self._is_running_as_queue_job():
            return super()._dispatch_sync_page(
                sync_log_id=sync_log_id,
                page=page,
                total_pages=total_pages,
                base_payload=base_payload,
                sync_to_str=sync_to_str,
                page_result=page_result,
                is_last_page=is_last_page,
            )
        desc = f"Zort sync page {page}/{total_pages}"
        self.with_delay(description=desc)._process_sync_page(
            sync_log_id=sync_log_id,
            page=page,
            total_pages=total_pages,
            base_payload=base_payload,
            sync_to_str=sync_to_str,
            page_result=page_result,
            is_last_page=is_last_page,
        )

    @api.model
    def _dispatch_pending_orders_batch(self, record_ids):
        """Override: dispatch as a queue job only when called from a queue job.

        If the ir.cron that triggered this run has ``run_as_queue_job`` enabled,
        ``job_uuid`` is present in context and each batch becomes an async job.
        Otherwise falls back to synchronous execution (base behaviour).
        """
        if not self._is_running_as_queue_job():
            return super()._dispatch_pending_orders_batch(record_ids)
        start = record_ids[0] if record_ids else "?"
        end = record_ids[-1] if record_ids else "?"
        desc = (
            f"Zort pending orders batch (ids {start}–{end}, {len(record_ids)} records)"
        )
        self.with_delay(description=desc)._process_pending_orders_batch(record_ids)
