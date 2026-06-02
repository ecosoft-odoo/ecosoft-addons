# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class APILog(models.Model):
    _name = "api.log"
    _inherit = ["mail.thread", "mail.activity.mixin"]
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
        data = data or ""
        result = result or ""
        ICP = self.env["ir.config_parameter"]
        limit = int(ICP.sudo().get_param("webhook.preview_limit", "2000"))

        self.data_size = len(data)
        self.data_preview = (data[:limit] + " ...") if len(data) > limit else data

        self.result_size = len(result)
        self.result_preview = (
            (result[:limit] + " ...") if len(result) > limit else result
        )

        if len(data) > limit or len(result) > limit:
            payload = json.dumps({"data": data, "result": result}, indent=2)
            attachment = self.env["ir.attachment"].create(
                {
                    "name": f"api_log_{self.id}.json",
                    "datas": base64.b64encode(payload.encode("utf-8")),
                    "res_model": self._name,
                    "res_id": self.id,
                    "mimetype": "application/json",
                }
            )
            self.attachment_id = attachment

    def unlink(self):
        self.mapped("attachment_id").unlink()
        return super().unlink()

    @api.model
    def autovacuum(self, days, chunk_size=None):
        """Delete all logs older than ``days``
        Called from a cron.
        """
        days = (days > 0) and int(days) or 0
        deadline = datetime.now() - timedelta(days=days)
        deadline_str = fields.Datetime.to_string(deadline)
        domain = [("create_date", "<=", deadline_str)]

        nb_records = self.env["api.log"].search_count(domain)

        if chunk_size:
            self.env.cr.execute(
                """
                WITH deleted AS (
                    DELETE FROM api_log
                    WHERE id IN (
                        SELECT id FROM api_log
                        WHERE create_date <= %s
                        ORDER BY create_date ASC
                        LIMIT %s
                    )
                    RETURNING id
                )
                DELETE FROM ir_attachment
                WHERE res_model = 'api.log' AND res_id IN (SELECT id FROM deleted)
                """,
                (deadline_str, chunk_size),
            )
        else:
            self.env.cr.execute(
                """
                WITH deleted AS (
                    DELETE FROM api_log WHERE create_date <= %s RETURNING id
                )
                DELETE FROM ir_attachment
                WHERE res_model = 'api.log' AND res_id IN (SELECT id FROM deleted)
                """,
                (deadline_str,),
            )

        _logger.info("AUTOVACUUM - %s 'api.log' records deleted", nb_records)
        return True

    def action_view_full_log(self):
        return {
            "name": self.env._("Attachment"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "form",
            "res_id": self.attachment_id.id,
        }
