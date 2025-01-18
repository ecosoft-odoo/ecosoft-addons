# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import datetime

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class LINEComposer(models.TransientModel):
    _name = "line.compose.message"
    _inherit = ["mail.thread", "line.service"]
    _description = "LINE composition wizard"

    # content
    message = fields.Text()
    template_id = fields.Many2one(
        comodel_name="line.template",
        index=True,
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="line_compose_message_ir_attachments_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Attachments",
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
    model = fields.Char(string="Related Document Model", index=True)
    res_id = fields.Integer(string="Related Document ID", index=True)

    def _set_global_dict(self, record):
        today = fields.Date.context_today(self)
        today_datetime = fields.Datetime.context_timestamp(
            self.env.user, datetime.now()
        )
        globals_dict = {
            "self": self,
            "record": record,
            "today": today,
            "today_datetime": today_datetime,
        }
        return globals_dict

    def _get_dynamic_type(self, template, record):
        """Convert value text to python code"""
        globals_dict = self._set_global_dict(record)
        value = safe_eval(template.dynamic_data, globals_dict=globals_dict)
        return value

    def _get_json_data_template(self, template, record):
        json_data = template.json_data
        if template.template_type == "dynamic":
            value = self._get_dynamic_type(template, record)
            json_data = json_data % value
        return json.loads(json_data)

    def _get_message_list(self, original_record=False):
        message_list = []
        # TODO: Support flex message and else
        if self.template_id:
            json_data = self._get_json_data_template(self.template_id, original_record)
            template_message = {
                "type": "flex",
                "altText": "test",  # TODO: no hardcode
                "contents": json_data,
            }
            message_list.append(template_message)
        elif self.message:
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
            message_list = self._get_message_list(original_record)
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
