# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, api, models


class WebhookUtils(models.AbstractModel):
    _inherit = "webhook.utils"

    @api.model
    def create_data(self, model, vals):
        if vals.get("run_job_queue"):
            # To avoid an infinite loop, remove the 'run_job_queue'
            del vals["run_job_queue"]
            job = self.with_delay().create_data(model, vals)
            return {
                "is_success": True,
                "job_uuid": job.uuid,
                "result": {},
                "messages": _("Record updated successfully"),
            }
        return super().create_data(model, vals)

    @api.model
    def create_update_data(self, model, vals):
        if vals.get("run_job_queue"):
            job = self.with_delay().create_update_data(model, vals)
            return {
                "is_success": True,
                "job_uuid": job.uuid,
                "result": {},
                "messages": _("Record updated successfully"),
            }
        return super().create_update_data(model, vals)
