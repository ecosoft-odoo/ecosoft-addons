# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    request_document_id = fields.Many2one(
        comodel_name="request.document",
        ondelete="cascade",
    )

    def write(self, vals):
        """Don't allow change value if request document is not done"""
        if self.env.context.get("allow_edit"):
            return super().write(vals)

        for rec in self:
            if rec.request_document_id and rec.request_document_id.state != "done":
                raise UserError(
                    self.env._(
                        "You cannot modify this record because the related "
                        "Request Document is not in 'Done' state."
                    )
                )
        return super().write(vals)


class HRExpense(models.Model):
    _inherit = "hr.expense"

    def _fields_exception(self):
        return {"date_commit", "amount_commit"}

    def write(self, vals):
        """Don't allow change value if request document is not done"""
        allowed_fields = self._fields_exception()
        if self.env.context.get("allow_edit") or all(
            field in allowed_fields for field in vals.keys()
        ):
            return super().write(vals)

        for rec in self:
            if not rec.sheet_id:
                continue

            if (
                rec.sheet_id.request_document_id
                and rec.sheet_id.request_document_id.state != "done"
            ):
                raise UserError(
                    self.env._(
                        "You cannot modify this record because the related "
                        "Request Document is not in 'Done' state."
                    )
                )
        return super().write(vals)
