# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PurposeCode(models.Model):
    _name = "purpose.code"
    _description = "Purpose Code follow INET convention."

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    reason = fields.Char(required=False)
    is_tax_invoice = fields.Boolean(string="Tax Invoice")
    is_credit_note = fields.Boolean(string="Credit Note")
    is_debit_note = fields.Boolean(string="Debit Note")
    is_receipt = fields.Boolean(string="Receipt")
    is_replacement = fields.Boolean(string="Replacement")

    @api.depends("name", "code")
    def name_get(self):
        res = []
        for rec in self:
            name = ("%(code)s - %(name)s") % {"code": rec.code, "name": rec.name}
            res.append((rec.id, name))
        return res
