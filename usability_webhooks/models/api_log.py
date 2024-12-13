# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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

    data = fields.Text(tracking=True)
    model = fields.Char(tracking=True)
    route = fields.Char(tracking=True)
    function_name = fields.Char(tracking=True)
    result = fields.Text(tracking=True)
    log_type = fields.Selection(
        selection=[
            ("send", "Send"),
            ("receive", "Receive"),
        ],
        default="receive",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="draft",
        tracking=True,
    )

    def action_call_api(self):
        try:
            func = getattr(self.env["webhook.utils"], self.function_name)
            res = func(self.model, json.loads(self.data))
            state = "done" if res["is_success"] else "failed"
            self.write({"result": res, "state": state})
        except Exception as e:
            res = {
                "is_success": False,
                "messages": e,
            }
            self.write({"result": res, "state": "failed"})
        return True

    @api.model
    def autovacuum(self, days, chunk_size=None):
        """Delete all logs older than ``days``
        Called from a cron.
        """
        days = (days > 0) and int(days) or 0
        deadline = datetime.now() - timedelta(days=days)
        domain = [("create_date", "<=", fields.Datetime.to_string(deadline))]

        # Count the number of records to be deleted
        nb_records = self.env["api.log"].search_count(domain)

        if chunk_size:
            # Use direct SQL query for deletion with limit
            query = """
                DELETE FROM api_log
                WHERE id IN (
                    SELECT id FROM api_log
                    WHERE create_date <= %s
                    ORDER BY create_date ASC
                    LIMIT %s
                )
            """
            self.env.cr.execute(
                query, (fields.Datetime.to_string(deadline), chunk_size)
            )
        else:
            # Use direct SQL query for deletion
            query = """
                DELETE FROM api_log
                WHERE create_date <= %s
            """
            self.env.cr.execute(query, (fields.Datetime.to_string(deadline),))

        _logger.info("AUTOVACUUM - %s 'api.log' records deleted", nb_records)
        return True
