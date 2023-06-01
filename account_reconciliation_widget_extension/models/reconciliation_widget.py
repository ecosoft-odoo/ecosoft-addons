# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def process_bank_statement_line(self, st_line_ids, data):
        ctx = self._context.copy()
        counterpart_aml_ids = []
        for datum in data:
            for aml_dict in datum.get("counterpart_aml_dicts", []):
                counterpart_aml_ids.append(aml_dict["counterpart_aml_id"])
        if counterpart_aml_ids:
            move_lines = self.env["account.move.line"].browse(counterpart_aml_ids)
            accounts = move_lines.mapped("account_id")
            # Allow skip_account_move_synchronization when
            # all type of accounts are set skip synchronization reconcile widget
            if all(
                account.user_type_id.skip_synchronization_reconcile_widget
                and account.reconcile
                for account in accounts
            ):
                ctx.update({"skip_account_move_synchronization": True})
        return super(
            AccountReconciliation, self.with_context(**ctx)
        ).process_bank_statement_line(st_line_ids, data)

    @api.model
    def _domain_move_lines_for_reconciliation(
        self,
        st_line,
        aml_accounts,
        partner_id,
        excluded_ids=None,
        search_str=False,
        mode="rp",
    ):
        domain = super()._domain_move_lines_for_reconciliation(
            st_line,
            aml_accounts,
            partner_id,
            excluded_ids=excluded_ids,
            search_str=search_str,
            mode=mode,
        )
        dom_filter = [("parent_state", "=", "posted")]
        # NOTE: not used because can't reconciled with misc journal
        # if st_line.statement_id.journal_id:
        #     dom_filter.append(("journal_id", "=", st_line.statement_id.journal_id.id))
        domain = expression.AND([domain, dom_filter])
        return domain

    @api.model
    def _process_move_lines(self, move_line_ids, new_mv_line_dicts):
        """Overwrite function for check skip_account_move_synchronization"""
        if len(move_line_ids) < 1 or len(move_line_ids) + len(new_mv_line_dicts) < 2:
            raise UserError(_("A reconciliation must involve at least 2 move lines."))

        account_move_line = self.env["account.move.line"].browse(move_line_ids)
        writeoff_lines = self.env["account.move.line"]
        # Allow skip_account_move_synchronization when
        # all type of accounts are set skip synchronization reconcile widget
        accounts = account_move_line.mapped("account_id")
        ctx = {}
        if all(
            account.user_type_id.skip_synchronization_reconcile_widget
            and account.reconcile
            for account in accounts
        ):
            ctx.update({"skip_account_move_synchronization": True})

        # Create writeoff move lines
        if len(new_mv_line_dicts) > 0:
            company_currency = account_move_line[0].account_id.company_id.currency_id
            same_currency = False
            currencies = list(
                {aml.currency_id or company_currency for aml in account_move_line}
            )
            if len(currencies) == 1 and currencies[0] != company_currency:
                same_currency = True
            # We don't have to convert debit/credit to currency as all values in
            # the reconciliation widget are displayed in company currency
            # If all the lines are in the same currency, create writeoff entry
            # with same currency also
            for mv_line_dict in new_mv_line_dicts:
                if not same_currency:
                    mv_line_dict["amount_currency"] = False
                writeoff_lines += account_move_line._create_writeoff([mv_line_dict])

            (account_move_line + writeoff_lines).reconcile()
        else:
            account_move_line.with_context(**ctx).reconcile()
