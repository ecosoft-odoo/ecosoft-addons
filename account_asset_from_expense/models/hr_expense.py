# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tests.common import Form


class HrExpense(models.Model):
    _inherit = "hr.expense"

    asset_profile_id = fields.Many2one(
        comodel_name="account.asset.profile",
        string="Asset Profile",
    )

    @api.onchange("account_id")
    def _onchange_account_id(self):
        if self.account_id.asset_profile_id:
            self.asset_profile_id = self.account_id.asset_profile_id

    @api.onchange("asset_profile_id")
    def _onchange_asset_profile_id(self):
        if self.asset_profile_id.account_asset_id:
            self.account_id = self.asset_profile_id.account_asset_id

    def _expense_expand_asset_line(self, line):
        self.ensure_one()
        amount = self.total_amount
        quantity = 1
        name = self.name
        company = self.company_id
        currency = self.currency_id
        account_date = (
            self.date
            or self.sheet_id.accounting_date
            or fields.Date.context_today(self)
        )

        if self.product_has_cost:
            amount = self.unit_amount
            quantity = self.quantity

        taxes = self.tax_ids.with_context(round=True).compute_all(
            amount, currency, quantity, self.product_id
        )

        total_qty = int(self.quantity) or 1
        total_amount_currency = taxes["total_excluded"]
        total_balance = currency._convert(
            total_amount_currency, company.currency_id, company, account_date
        )

        unit_amount_currency = currency.round(total_amount_currency / total_qty)
        unit_balance = company.currency_id.round(total_balance / total_qty)

        lines = []
        accumulated_currency = 0.0
        accumulated_balance = 0.0

        for i in range(1, total_qty + 1):
            cpy_line = line.copy()

            if i == total_qty:
                line_amount_currency = total_amount_currency - accumulated_currency
                line_balance = total_balance - accumulated_balance
            else:
                line_amount_currency = unit_amount_currency
                line_balance = unit_balance

            accumulated_currency += line_amount_currency
            accumulated_balance += line_balance

            cpy_line.update(
                {
                    "name": f"{name} {i}",
                    "quantity": 1,
                    "debit": line_balance if line_balance > 0 else 0,
                    "credit": -line_balance if line_balance < 0 else 0,
                    "amount_currency": line_amount_currency,
                }
            )
            lines.append(cpy_line)
        return lines

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self.filtered("asset_profile_id"):
            asset_lines = []
            old_asset_line = dict()
            for line in move_line_values_by_expense[expense.id]:
                if line["account_id"] == expense.asset_profile_id.account_asset_id.id:
                    line["asset_profile_id"] = expense.asset_profile_id.id
                    if expense.asset_profile_id.asset_product_item:
                        old_asset_line = line
                        asset_lines.extend(expense._expense_expand_asset_line(line))
            if asset_lines:
                if old_asset_line:
                    move_line_values_by_expense[expense.id].remove(old_asset_line)
                move_line_values_by_expense[expense.id].extend(asset_lines)
        return move_line_values_by_expense

    def action_move_create(self):
        move_group_by_sheet = super().action_move_create()
        for sheet in move_group_by_sheet:
            for move in move_group_by_sheet[sheet]:
                for aml in move.line_ids.filtered("asset_profile_id"):
                    vals = move._prepare_asset_vals(aml)
                    asset_form = Form(
                        self.env["account.asset"]
                        .with_company(move.company_id)
                        .with_context(create_asset_from_move_line=True, move_id=move.id)
                    )
                    for key, val in vals.items():
                        setattr(asset_form, key, val)
                    asset = asset_form.save()
                    asset.analytic_tag_ids = aml.analytic_tag_ids
                    aml.with_context(allow_asset=True).asset_id = asset.id
                refs = [
                    (
                        f"<a href=# data-oe-model=account.asset "
                        f"data-oe-id={name_get[0]}>{name_get[1]}</a>"
                    )
                    for name_get in move.line_ids.filtered(
                        "asset_profile_id"
                    ).asset_id.name_get()
                ]
                if refs:
                    message = _("This expense created the asset(s): %s") % ", ".join(
                        refs
                    )
                    move.message_post(body=message)
        return move_group_by_sheet
