# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TrialBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.trial_balance"

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys():
            # Mapping report data
            trial_balance = res_data["trial_balance"]
            trial_balance = self._get_report_data_mapping(
                trial_balance, data["map_type_id"]
            )
            res_data["trial_balance"] = trial_balance
            # Mapping account data
            accounts_data = res_data["accounts_data"]
            accounts_data = self._get_account_data_mapping(
                accounts_data, data["map_type_id"]
            )
            res_data["accounts_data"] = accounts_data
        return res_data
