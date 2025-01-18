# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class LINETemplate(models.Model):
    _name = "line.template"
    _description = "LINE Templates"

    name = fields.Char(
        required=True,
    )
    template_model = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
    )
    template_type = fields.Selection(
        selection=[
            ("static", "Static"),
            ("dynamic", "Dynamic"),
        ],
        default="static",
        required=True,
    )
    dynamic_data = fields.Text()
    json_data = fields.Text()
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
    )

    def action_format_json(self):
        pass
        # TODO: Format json
        # for record in self:
        #     try:
        #         json_data = json.loads(cleaned_json)
        #         # Format the JSON data as a pretty-printed JSON string
        #         formatted_json = json.dumps(json_data, indent=4)

        #         record.json_data = f'<pre>{formatted_json}</pre>'
        #     except ValueError as e:
        #         # Handle invalid JSON errors
        #         raise UserError(_(f"Invalid JSON: {str(e)}"))
