# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Message(models.Model):
    _inherit = "mail.message"

    message_type = fields.Selection(
        selection_add=[("line", "LINE Notification")], ondelete={"line": "cascade"}
    )
    line_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_message_res_partner_line_rel",
        column1="message_id",
        column2="partner_id",
        context={"active_test": False},
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        message_type = 'line' will be pushed to LINE
        Format: message_type = 'line', line_partner_ids = list of partner_id
        """
        for vals in vals_list:
            if vals.get("message_type") == "line" and vals.get("line_partner_ids"):
                self.env["base.line.process"].message_line_push(
                    vals["body"], vals.get("line_partner_ids")
                )
                # Logs message with text only (attachment will use standard message)
                message_text = [
                    body["text"] for body in vals["body"] if body.get("type") == "text"
                ]
                vals["body"] = "\n".join(message_text)
                # TODO: May be add log here?
        return super().create(vals_list)
