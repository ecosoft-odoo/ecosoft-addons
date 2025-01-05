# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LINEMessage(models.Model):
    _name = "line.message"
    _description = "LINE Message"
    _order = "create_date desc"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        # required=True,
        ondelete="cascade",
    )
    log_type = fields.Selection(
        selection=[
            ("receive", "Receive"),
            ("send", "Send"),
        ],
        default="receive",
    )
    is_broadcast = fields.Boolean(
        string="Broadcast",
    )
    message_type = fields.Selection(
        selection=[
            ("text", "Text"),
            ("image", "Image"),
            ("video", "Video"),
            ("audio", "Audio"),
            ("file", "File"),
            ("location", "Location"),
            ("sticker", "Sticker"),
        ],
        required=True,
    )
    message = fields.Text(
        required=True,
    )
    message_error = fields.Text(
        string="Error Message",
    )
    state = fields.Selection(
        selection=[
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        default="sent",
        string="Status",
    )

    @api.model
    def autovacuum(self, days, chunk_size=None):
        """Delete all logs older than ``days``
        Called from a cron.
        """
        days = (days > 0) and int(days) or 0
        deadline = datetime.now() - timedelta(days=days)
        domain = [("create_date", "<=", fields.Datetime.to_string(deadline))]

        # Count the number of records to be deleted
        nb_records = self.env["line.message"].search_count(domain)

        if chunk_size:
            # Use direct SQL query for deletion with limit
            query = """
                DELETE FROM line_message
                WHERE id IN (
                    SELECT id FROM line_message
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
                DELETE FROM line_message
                WHERE create_date <= %s
            """
            self.env.cr.execute(query, (fields.Datetime.to_string(deadline),))

        _logger.info("AUTOVACUUM - %s 'line.message' records deleted", nb_records)
        return True
