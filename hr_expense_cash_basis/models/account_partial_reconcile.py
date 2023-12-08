# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _create_tax_cash_basis_moves_expense(self):
        """OVERWRITE core function odoo to support cash basis from expense
        Core Odoo
            Expense Sheet:
                EX1     20.0    Undue Vat7%
                EX2     30.0    Undue Vat7%
                EX3     40.0
            When register payment, it will create cash basis
            following lines of expense sheet and allocated with percent.
        Fix module:
            When register payment, it will create cash basis
            following lines of undue vat expense sheet
        """
        tax_cash_basis_values_per_move = self._collect_tax_cash_basis_values()
        today = fields.Date.context_today(self)

        moves_to_create = []
        to_reconcile_after = []
        for move_values in tax_cash_basis_values_per_move.values():
            move = move_values["move"]
            pending_cash_basis_lines = []
            partial_duplicate_expense = []
            for partial_values in move_values["partials"]:
                partial = partial_values["partial"]
                if (
                    not any(
                        x.tax_exigibility == "on_payment"
                        for x in partial.credit_move_id.expense_id.tax_ids
                    )
                    or partial.credit_move_id.expense_id in partial_duplicate_expense
                ):
                    continue
                partial_duplicate_expense.append(partial.credit_move_id.expense_id)
                # Init the journal entry.
                lock_date = move.company_id._get_user_fiscal_lock_date()
                move_date = (
                    partial.max_date
                    if partial.max_date > (lock_date or date.min)
                    else today
                )
                move_vals = {
                    "move_type": "entry",
                    "date": move_date,
                    "ref": move.name,
                    "journal_id": partial.company_id.tax_cash_basis_journal_id.id,
                    "line_ids": [],
                    "tax_cash_basis_rec_id": partial.id,
                    "tax_cash_basis_origin_move_id": move.id,
                    "fiscal_position_id": move.fiscal_position_id.id,
                }
                # Tracking of lines grouped all together.
                # Used to reduce the number of generated lines and to avoid rounding issues.
                partial_lines_to_create = {}
                for caba_treatment, line in move_values["to_process_lines"]:
                    if (
                        caba_treatment != "tax"
                        or line.tax_base_amount
                        != partial.credit_move_id.expense_id.untaxed_amount
                    ):
                        continue
                    # ==========================================================================
                    # Compute the balance of the current line on the cash basis entry.
                    # This balance is a percentage representing the part of the journal entry
                    # that is actually paid by the current partial.
                    # ==========================================================================

                    # Percentage expressed in the foreign currency.
                    amount_currency = line.currency_id.round(line.amount_currency)
                    balance = (
                        partial_values["payment_rate"]
                        and amount_currency / partial_values["payment_rate"]
                        or 0.0
                    )

                    # ==========================================================================
                    # Prepare the mirror cash basis journal item of the current line.
                    # Group them all together as much as possible to reduce the number of
                    # generated journal items.
                    # Also track the computed balance in order to avoid rounding issues when
                    # the journal entry will be fully paid. At that case, we expect the exact
                    # amount of each line has been covered by the cash basis journal entries
                    # and well reported in the Tax Report.
                    # ==========================================================================
                    # Tax line.
                    cb_line_vals = self._prepare_cash_basis_tax_line_vals(
                        line, balance, amount_currency
                    )
                    grouping_key = self._get_cash_basis_tax_line_grouping_key_from_vals(
                        cb_line_vals
                    )

                    if grouping_key in partial_lines_to_create:
                        aggregated_vals = partial_lines_to_create[grouping_key]["vals"]
                        debit = aggregated_vals["debit"] + cb_line_vals["debit"]
                        credit = aggregated_vals["credit"] + cb_line_vals["credit"]
                        balance = debit - credit

                        aggregated_vals.update(
                            {
                                "debit": balance if balance > 0 else 0,
                                "credit": -balance if balance < 0 else 0,
                                "amount_currency": aggregated_vals["amount_currency"]
                                + cb_line_vals["amount_currency"],
                            }
                        )
                        if caba_treatment == "tax":
                            aggregated_vals.update(
                                {
                                    "tax_base_amount": aggregated_vals[
                                        "tax_base_amount"
                                    ]
                                    + cb_line_vals["tax_base_amount"],
                                }
                            )
                            partial_lines_to_create[grouping_key]["tax_line"] += line
                    else:
                        partial_lines_to_create[grouping_key] = {
                            "vals": cb_line_vals,
                        }
                        if caba_treatment == "tax":
                            partial_lines_to_create[grouping_key].update(
                                {
                                    "tax_line": line,
                                }
                            )

                # ==========================================================================
                # Create the counterpart journal items.
                # ==========================================================================

                # To be able to retrieve the correct matching between the tax lines to reconcile
                # later, the lines will be created using a specific sequence.
                sequence = 0

                for grouping_key, aggregated_vals in partial_lines_to_create.items():
                    line_vals = aggregated_vals["vals"]
                    line_vals["sequence"] = sequence

                    pending_cash_basis_lines.append(
                        (grouping_key, line_vals["amount_currency"])
                    )

                    if "tax_repartition_line_id" in line_vals:
                        # Tax line.

                        tax_line = aggregated_vals["tax_line"]
                        counterpart_line_vals = (
                            self._prepare_cash_basis_counterpart_tax_line_vals(
                                tax_line, line_vals
                            )
                        )
                        counterpart_line_vals["sequence"] = sequence + 1

                        if tax_line.account_id.reconcile:
                            move_index = len(moves_to_create)
                            to_reconcile_after.append(
                                (
                                    tax_line,
                                    move_index,
                                    counterpart_line_vals["sequence"],
                                )
                            )
                        sequence += 2
                        move_vals["line_ids"] += [
                            (0, 0, counterpart_line_vals),
                            (0, 0, line_vals),
                        ]
                moves_to_create.append(move_vals)
        moves = self.env["account.move"].create(moves_to_create)
        return moves

    def _create_tax_cash_basis_moves(self):
        if any(partial.credit_move_id.expense_id for partial in self):
            move_lines = self.debit_move_id | self.credit_move_id
            payment = move_lines.mapped("payment_id")
            if len(payment) == 1:
                self = self.with_context(payment_id=payment.id)
            return self._create_tax_cash_basis_moves_expense()
        return super()._create_tax_cash_basis_moves()