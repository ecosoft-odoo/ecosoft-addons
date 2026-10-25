# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class APILog(models.Model):
    _name = "api.log"
    _inherit = ("mail.thread", "mail.activity.mixin")
    _description = "API Logs"
    _rec_name = "id"
    _order = "id desc"

    model = fields.Char()
    res_model = fields.Char(string="Record Model")
    res_id = fields.Integer(string="Record ID")
    callback_url = fields.Char(string="Callback URL")
    route = fields.Char()
    function_name = fields.Char()
    log_type = fields.Selection(
        selection=[
            ("send", "Send"),
            ("receive", "Receive"),
        ],
        default="receive",
    )
    data_preview = fields.Text(string="Request Preview")
    data_size = fields.Integer(string="Request Size")
    result_preview = fields.Text(string="Response Preview")
    result_size = fields.Integer(string="Response Size")
    attachment_id = fields.Many2one(comodel_name="ir.attachment", string="Full Payload")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="draft",
        tracking=True,
    )

    def _save_payload(self, data, result):
        self.ensure_one()
        data = data or ""
        result = result or ""
        limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_int("webhook.preview_limit", 2000)
        )

        def preview(text):
            return (text[:limit] + " ...") if len(text) > limit else text

        vals = {
            "data_size": len(data),
            "data_preview": preview(data),
            "result_size": len(result),
            "result_preview": preview(result),
        }
        if len(data) > limit or len(result) > limit:
            payload = json.dumps({"data": data, "result": result}, indent=2)
            vals["attachment_id"] = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": f"api_log_{self.id}.json",
                        "raw": payload.encode(),
                        "res_model": self._name,
                        "res_id": self.id,
                        "mimetype": "application/json",
                    }
                )
                .id
            )
        self.sudo().write(vals)

    @api.model
    def autovacuum(self, days, chunk_size=None):
        """Delete all logs older than ``days``, at most ``chunk_size`` per call.
        Called from a cron.

        Deleted through the ORM, so attachment files and chatter of the logs
        are cleaned up too.
        """
        deadline = fields.Datetime.now() - timedelta(days=max(int(days), 0))
        logs = self.sudo().search(
            [("create_date", "<=", deadline)],
            order="create_date, id",
            limit=chunk_size or None,
        )
        nb_records = len(logs)
        logs.unlink()
        _logger.info("AUTOVACUUM - %s 'api.log' records deleted", nb_records)
        return True

    def action_view_full_log(self):
        self.ensure_one()
        return {
            "name": self.env._("Attachment"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "form",
            "res_id": self.attachment_id.id,
        }
