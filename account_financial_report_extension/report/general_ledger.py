# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class GeneralLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.general_ledger"

    def _get_merge_data(self):
        return [
            "move_lines",
        ]

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        general_ledger = res_data["general_ledger"]
        if "map_type_id" in data.keys():
            merge_data = self._get_merge_data()
            general_ledger = self._get_report_data_mapping(
                general_ledger, data["map_type_id"], merge_data
            )
        res_data["general_ledger"] = general_ledger
        return res_data
