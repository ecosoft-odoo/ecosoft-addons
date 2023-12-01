from odoo import _, models
from odoo.exceptions import UserError


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _collect_tax_cash_basis_values(self):
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
        tax_cash_basis_values_per_move = {}

        if not self:
            return {}

        total_cash_basis = 0.0
        for partial in self:
            if partial.credit_move_id.expense_id and any(
                x.tax_exigibility == "on_payment"
                for x in partial.credit_move_id.expense_id.tax_ids
            ):
                total_cash_basis += partial.amount

        for partial in self:
            if partial.credit_move_id.expense_id and not any(
                x.tax_exigibility == "on_payment"
                for x in partial.credit_move_id.expense_id.tax_ids
            ):
                continue

            for move in {partial.debit_move_id.move_id, partial.credit_move_id.move_id}:

                # Collect data about cash basis.
                if move.id not in tax_cash_basis_values_per_move:
                    tax_cash_basis_values_per_move[
                        move.id
                    ] = move._collect_tax_cash_basis_values()

                # Nothing to process on the move.
                if not tax_cash_basis_values_per_move.get(move.id):
                    continue
                move_values = tax_cash_basis_values_per_move[move.id]

                # Check the cash basis configuration only when at least one cash basis tax entry need to be created.
                journal = partial.company_id.tax_cash_basis_journal_id

                if not journal:
                    raise UserError(
                        _(
                            "There is no tax cash basis journal defined for the '%s' company.\n"
                            "Configure it in Accounting/Configuration/Settings"
                        )
                        % partial.company_id.display_name
                    )

                partial_amount = 0.0
                partial_amount_currency = 0.0
                rate_amount = 0.0
                rate_amount_currency = 0.0

                if partial.debit_move_id.move_id == move:
                    partial_amount += partial.amount
                    partial_amount_currency += partial.debit_amount_currency
                    rate_amount -= partial.credit_move_id.balance
                    rate_amount_currency -= partial.credit_move_id.amount_currency
                    source_line = partial.debit_move_id
                    counterpart_line = partial.credit_move_id

                if partial.credit_move_id.move_id == move:
                    partial_amount += partial.amount
                    partial_amount_currency += partial.credit_amount_currency
                    rate_amount += partial.debit_move_id.balance
                    rate_amount_currency += partial.debit_move_id.amount_currency
                    source_line = partial.credit_move_id
                    counterpart_line = partial.debit_move_id

                if partial.debit_move_id.move_id.is_invoice(
                    include_receipts=True
                ) and partial.credit_move_id.move_id.is_invoice(include_receipts=True):
                    # Will match when reconciling a refund with an invoice.
                    # In this case, we want to use the rate of each businness document to compute its cash basis entry,
                    # not the rate of what it's reconciled with.
                    rate_amount = source_line.balance
                    rate_amount_currency = source_line.amount_currency
                    payment_date = move.date
                else:
                    payment_date = counterpart_line.date

                if move_values["currency"] == move.company_id.currency_id:
                    if not total_cash_basis:
                        total_cash_basis = 1
                    # Percentage made on company's currency.
                    percentage = partial_amount / total_cash_basis
                else:
                    # Percentage made on foreign currency.
                    percentage = (
                        partial_amount_currency / move_values["total_amount_currency"]
                    )

                if source_line.currency_id != counterpart_line.currency_id:
                    # When the invoice and the payment are not sharing the same foreign currency, the rate is computed
                    # on-the-fly using the payment date.
                    payment_rate = self.env["res.currency"]._get_conversion_rate(
                        counterpart_line.company_currency_id,
                        source_line.currency_id,
                        counterpart_line.company_id,
                        payment_date,
                    )
                elif rate_amount:
                    payment_rate = rate_amount_currency / rate_amount
                else:
                    payment_rate = 0.0

                partial_vals = {
                    "partial": partial,
                    "percentage": percentage,
                    "payment_rate": payment_rate,
                }

                # Add partials.
                move_values.setdefault("partials", [])
                move_values["partials"].append(partial_vals)

        # Clean-up moves having nothing to process.
        return {k: v for k, v in tax_cash_basis_values_per_move.items() if v}
