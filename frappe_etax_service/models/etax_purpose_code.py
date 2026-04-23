# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ETaxPurposeCode(models.Model):
    _name = "etax.purpose.code"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Purpose Code follow INET convention."
    _order = "code, name"
    _rec_names_search = ["code", "name"]

    name = fields.Char(
        required=True,
        tracking=True,
    )
    code = fields.Char(
        required=True,
        tracking=True,
    )
    reason = fields.Char(tracking=True)
    etax_doctype_code_ids = fields.Many2many(
        comodel_name="etax.doctype.code",
        string="Applicable Doctype Codes",
        tracking=True,
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.name}"
