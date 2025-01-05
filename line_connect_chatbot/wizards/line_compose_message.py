# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class LINEComposer(models.TransientModel):
    _name = "line.compose.message"
    _inherit = ["mail.thread", "line.service"]
    _description = "LINE composition wizard"

    # content
    message = fields.Text()
    # template_id = fields.Many2one(
    #     'mail.template', 'Use template', index=True,
    #     domain="[('model', '=', model)]")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "line_compose_message_ir_attachments_rel",
        "wizard_id",
        "attachment_id",
        "Attachments",
    )
    message_type = fields.Selection(
        selection=[
            ("text", "Text"),
            ("broadcast", "Broadcast"),
        ],
        default="text",
        required=True,
    )

    # destination
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="line_compose_message_res_partner_rel",
        column1="wizard_id",
        column2="partner_id",
        string="LINE to",
        domain="[('line_access_token', '!=', False)]",
    )

    model = fields.Char("Related Document Model", index=True)
    res_id = fields.Integer("Related Document ID", index=True)

    def _get_message_list(self):
        message_list = []
        # TODO: Support flex message and else
        if self.message:
            message_list.append(
                {
                    "type": "text",
                    "text": self.message,
                }
            )
        attachments = self.attachment_ids
        if attachments:
            message_list = self.message_line_attachment(attachments, message_list)
        return message_list

    def send_broadcast_message(self):
        message_list = self._get_message_list()
        self.message_line_push(message_list, broadcast=True)

    def send_message(self):
        if self.model and self.res_id:
            original_record = self.env[self.model].browse(self.res_id)
            message_list = self._get_message_list()
            original_record.message_post(
                body=message_list,
                message_type="line",
                line_partner_ids=self.partner_ids.ids,
                attachment_ids=self.attachment_ids.ids,
            )

    def action_send_line(self):
        self.ensure_one()
        if self.message_type == "broadcast":
            self.send_broadcast_message()
        else:
            self.send_message()
        return
