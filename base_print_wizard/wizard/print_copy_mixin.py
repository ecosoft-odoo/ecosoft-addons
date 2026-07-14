# Copyright 2026 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PrintCopyMixin(models.AbstractModel):
    _name = "base.print.copy.mixin"
    _description = "Print Copy Options Mixin"

    copy_qty = fields.Integer(
        string="Copies",
        default=1,
        required=True,
    )
    copy_type = fields.Selection(
        selection=[
            ("original", "Original"),
            ("copy", "Copy"),
        ],
        string="Type",
    )

    @api.constrains("copy_qty")
    def _check_copy_qty(self):
        if any(wizard.copy_qty < 1 for wizard in self):
            raise ValidationError(self.env._("Copies must be greater than zero."))

    def _get_copy_report_context(self):
        self.ensure_one()
        return {
            "copy_qty": self.copy_qty,
            "copy_type": self.copy_type,
        }
