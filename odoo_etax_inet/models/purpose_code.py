# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PurposeCode(models.Model):
    _name = "purpose.code"
    _description = "Purpose Code follow INET convention."

    name = fields.Char(required=True)
    code = fields.Char()

    @api.depends("name", "code")
    def name_get(self):
        res = []
        for rec in self:
            name = ("%(code)s - %(name)s") % {"code": rec.code, "name": rec.name}
            res.append((rec.id, name))
        return res
