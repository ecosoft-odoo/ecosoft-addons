# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LINETemplate(models.Model):
    _name = "line.template"
    _parent_name = "parent_id"
    _parent_store = True

    _description = "LINE Templates"

    name = fields.Char(
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name="line.template", index=True, ondelete="cascade"
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        comodel_name="line.template",
        inverse_name="parent_id",
        string="Child Template",
    )
    template_model = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
    )
    template_default = fields.Boolean(copy=False)
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
    alt_text = fields.Char()
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
    )

    @api.constrains("template_model", "template_default")
    def _check_template_model_default(self):
        LineTemplate = self.env["line.template"]
        for record in self:
            if record.template_model and record.template_default:
                existing_records = LineTemplate.search_count(
                    [
                        ("template_model", "=", record.template_model.id),
                        ("template_default", "=", True),
                        ("id", "!=", record.id),  # Exclude the current record
                    ]
                )
                if existing_records:
                    raise UserError(
                        _(
                            "Only one record can be set as default "
                            "for the model '%(model)s'."
                        )
                        % {"model": record.template_model.name}
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
