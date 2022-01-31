# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OpenItemsReport(models.AbstractModel):
    _inherit = "report.account_financial_report.open_items"

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
        Open_Items = res_data["Open_Items"]
        if "map_type_id" in data.keys():
            merge_data = self._get_merge_data()
            Open_Items = self._get_report_data_mapping(
                Open_Items, data["map_type_id"], merge_data
            )
        res_data["Open_Items"] = Open_Items
        return res_data
