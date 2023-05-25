# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import itertools

from odoo import models


class TrialBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.trial_balance"

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys() and data["map_type_id"]:
            map_type = self.env["data.map.type"].browse(data["map_type_id"])
            # Mapping report data
            trial_balance = res_data["trial_balance"]
            trial_balance = map_type._get_report_data_mapping_afr(trial_balance)
            # Summary data mapping
            result = []
            for key, group in itertools.groupby(
                trial_balance, key=lambda x: (x["code"], x["name"])
            ):
                group = list(group)
                # Get sum groupby name, code
                sum_initial_balance = 0.0
                sum_credit = 0.0
                sum_debit = 0.0
                sum_balance = 0.0
                sum_ending_balance = 0.0
                for item in group:
                    sum_initial_balance += item["initial_balance"]
                    sum_credit += item["credit"]
                    sum_debit += item["debit"]
                    sum_balance += item["balance"]
                    sum_ending_balance += item["ending_balance"]
                result.append(
                    {
                        "id": group[0]["id"],
                        "code": key[0],
                        "name": key[1],
                        "hide_account": group[0]["hide_account"],
                        "group_id": group[0]["group_id"],
                        "currency_id": group[0]["currency_id"],
                        "currency_name": group[0]["currency_name"],
                        "centralized": group[0]["centralized"],
                        "initial_balance": sum_initial_balance,
                        "credit": sum_credit,
                        "debit": sum_debit,
                        "balance": sum_balance,
                        "ending_balance": sum_ending_balance,
                        "type": group[0]["type"],
                    }
                )
            res_data["trial_balance"] = result
            # Mapping account data
            accounts_data = res_data["accounts_data"]
            accounts_data = map_type._get_account_data_mapping_afr(accounts_data)
            res_data["accounts_data"] = accounts_data
        return res_data
