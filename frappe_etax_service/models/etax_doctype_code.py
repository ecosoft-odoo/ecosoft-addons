# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ETaxDoctypeCode(models.Model):
    _name = "etax.doctype.code"
    _description = "Standard eTax Document Type Code (INET)"
    _order = "code"
    _rec_names_search = ["name", "code"]

    code = fields.Char(required=True)
    name = fields.Char(required=True)

    _sql_constraints = [
        ("code_uniq", "UNIQUE(code)", "Doctype code must be unique"),
    ]

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.name}"
