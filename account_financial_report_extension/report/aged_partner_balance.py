# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AgedPartnerBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.aged_partner_balance"

    def _get_merge_data(self):
        return [
            "residual",
            "current",
            "30_days",
            "60_days",
            "90_days",
            "120_days",
            "older",
        ]

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        aged_partner_balance = res_data["aged_partner_balance"]
        if "map_type_id" in data.keys():
            merge_data = self._get_merge_data()
            aged_partner_balance = self._get_report_data_mapping(
                aged_partner_balance, data["map_type_id"], merge_data
            )
        res_data["aged_partner_balance"] = aged_partner_balance
        return res_data
