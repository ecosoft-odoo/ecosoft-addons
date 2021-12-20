# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

READONLY_STATES = {
    "post": [("readonly", True)],
    "done": [("readonly", True)],
    "cancel": [("readonly", True)],
}


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    clearing_count = fields.Integer(compute="_compute_clearing_count")
    name = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.constrains("operating_unit_id")
    def check_operating_unit_id(self):
        for rec in self:
            for line in rec.expense_line_ids:
                if (
                    line.operating_unit_id
                    not in line.analytic_account_id.operating_unit_ids
                ):
                    raise UserError(
                        _(
                            "Configuration error. The Operating Unit in"
                            " the Analytic Account Line must be the same."
                        )
                    )

    def _compute_clearing_count(self):
        for expense in self:
            expense.clearing_count = len(expense.clearing_sheet_ids.ids)

    def action_get_clearing_sheet_ids(self):
        self.ensure_one()
        action = {
            "name": _("Clearing"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense.sheet",
            "target": "current",
        }
        clearing_sheet_ids = self.clearing_sheet_ids.ids
        view = self.env.ref("hr_expense.view_hr_expense_sheet_form")
        if len(clearing_sheet_ids) == 1:
            expense = clearing_sheet_ids[0]
            action["res_id"] = expense
            action["view_mode"] = "form"
            action["views"] = [(view.id, "form")]
        else:
            action["view_mode"] = "tree,form"
            action["domain"] = [("id", "in", clearing_sheet_ids)]
        return action

    @api.onchange("advance_sheet_id")
    def _onchange_advance_sheet_id(self):
        super()._onchange_advance_sheet_id()
        if self.advance_sheet_id:
            self.name = self.advance_sheet_id.name


class HRExpense(models.Model):
    _inherit = "hr.expense"

    product_id = fields.Many2one(
        comodel_name="product.product",
        default=lambda self: self.env.ref("hr_expense.product_product_fixed_cost"),
    )
    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        states=READONLY_STATES,
    )
    clearing_activity_id = fields.Many2one(
        comodel_name="budget.activity",
        states=READONLY_STATES,
    )

    @api.onchange("clearing_activity_id")
    def _onchange_clearing_activity_id(self):
        expense_product = self.env.ref("hr_expense.product_product_fixed_cost")
        for expense in self:
            expense.clearing_product_id = (
                expense.clearing_activity_id and expense_product.id or False
            )

    @api.depends("product_id", "company_id")
    def _compute_from_product_id_company_id(self):
        """ Clear default name on expense """
        res = super()._compute_from_product_id_company_id()
        if self._context.get("skip_clear_default_name", False):
            return res
        for expense in self:
            expense.name = False
        return res
