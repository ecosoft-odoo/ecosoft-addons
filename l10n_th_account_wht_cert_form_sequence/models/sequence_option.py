# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrSequenceOption(models.Model):
    _inherit = "ir.sequence.option"

    model = fields.Selection(
        selection_add=[("withholding.tax.cert", "withholding.tax.cert")],
        ondelete={"withholding.tax.cert": "cascade"},
    )
