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

    def _get_dynamic_type(self, field_dynamic, record):
        """Convert value text to python code"""
        globals_dict = self._set_global_dict(record)
        value = safe_eval(field_dynamic, globals_dict=globals_dict)
        return value

    def _get_child_template(self, template, record, list_data):
        for child in template.child_ids:
            if child.template_type == "dynamic":
                value = self._get_dynamic_type(child.dynamic_data, record)
                json_data = child.json_data % value
            else:
                json_data = child.json_data
            json_data = json.loads(json_data.replace("'", '"'))
            if isinstance(json_data, list):
                list_data.extend(json_data)
            else:
                list_data.append(json_data)
        return list_data

    def _get_json_data_template(self, template, record):
        json_data = template.json_data
        if template.template_type == "dynamic":
            value = self._get_dynamic_type(template.dynamic_data, record)
            json_data = json_data % value
        # Convert to list of dict
        list_data = [json.loads(json_data)]

        # Check child of template
        list_data = self._get_child_template(template, record, list_data)
        return list_data

    def _get_attachment(self, message_list):
        attachments = self.attachment_ids
        if attachments:
            message_list = self.message_line_attachment(attachments, message_list)
        return message_list

    def _get_message_list(self, original_record=False):
        message_list = []
        if self.template_id:
            list_json_data = self._get_json_data_template(
                self.template_id, original_record
            )
            alt_text = self.template_id.alt_text
            if self.template_id.template_type == "dynamic":
                value = self._get_dynamic_type(
                    self.template_id.dynamic_data, original_record
                )
                alt_text = alt_text % value
            template_message = {
                "type": "flex",
                "altText": alt_text,
                "contents": {
                    "type": "carousel",  # support with flex or carousel
                    "contents": list_json_data,
                },
            }
            message_list.append(template_message)
        elif self.message:
            message_list.append(
                {
                    "type": "text",
                    "text": self.message,
                }
            )
        message_list = self._get_attachment(message_list)
        return message_list

    def send_broadcast_message(self):
        message_list = self._get_message_list()
        self.message_line_action(message_list, "broadcast")

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
