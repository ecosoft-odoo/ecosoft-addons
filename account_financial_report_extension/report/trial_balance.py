# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TrialBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.trial_balance"

    def _get_merge_data(self):
        return [
            "initial_balance",
            "credit",
            "debit",
            "balance",
            "ending_balance",
        ]

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys():
            trial_balance = res_data["trial_balance"]
            merge_data = self._get_merge_data()
            trial_balance = self._get_report_data_mapping(
                trial_balance, data["map_type_id"], merge_data
            )
            res_data["trial_balance"] = trial_balance
        return res_data
