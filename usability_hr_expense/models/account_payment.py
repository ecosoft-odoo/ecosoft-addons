# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ For case expense: not used self balance OU, add OU in all move line """
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)
        if self.expense_sheet_ids:
            ou_expense_sheet = self.expense_sheet_ids.mapped("operating_unit_id")
            if len(ou_expense_sheet) > 1:
                raise UserError(_("Expense Sheet must be 1 operating unit."))
            for line in line_vals_list:
                line["operating_unit_id"] = (
                    ou_expense_sheet and ou_expense_sheet.id or False
                )
        return line_vals_list

    def _synchronize_to_moves(self, changed_fields):
        res = super()._synchronize_to_moves(changed_fields)
        for pay in self.with_context(skip_account_move_synchronization=True):
            line_ou = pay.move_id.line_ids.mapped("operating_unit_id")
            if len(line_ou.ids) > 1:
                raise UserError(_("Found OU > 1 operating unit."))
            if not pay.move_id.operating_unit_id:
                pay.move_id.operating_unit_id = line_ou and line_ou.id or False
        return res