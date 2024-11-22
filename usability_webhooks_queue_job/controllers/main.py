# Copyright 2024 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.http import request

from odoo.addons.usability_webhooks.controllers.main import WebhookController


class WebhookControllerJob(WebhookController):
    def _call_function_api(self, model, vals, function):
        """
        ==================================
        Example Format for Job Queue
        ==================================
        {
            "params": {
                "model": "<model name>",
                "vals": {
                    "payload": {
                        // Your payload data here
                    },
                    "queue_job": {
                        "run_queue": True,  # Enable job queue processing
                        # Optional, defaults to "root.webhook_api"
                        "channel": "<channel name>",
                    }
                }
            }
        }
        """
        if vals.get("queue_job") and vals["queue_job"].get("run_queue"):
            channel = (
                vals["queue_job"].get("channel", False) or "root.webhook_api"
            )  # standard channel
            job = getattr(
                request.env["webhook.utils"].with_delay(channel=channel), function
            )(model, vals)
            return {
                "is_success": True,
                "job_uuid": job.uuid,
                "channel": channel,
                "result": {},
                "messages": _("Record run job queue successfully"),
            }
        return super()._call_function_api(model, vals, function)
