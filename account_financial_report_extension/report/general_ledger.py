# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class GeneralLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.general_ledger"

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys() and data["map_type_id"]:
            map_type = self.env["data.map.type"].browse(data["map_type_id"])
            # Mapping report data
            general_ledger = res_data["general_ledger"]
            general_ledger = map_type._get_report_data_mapping_afr(
                general_ledger
            )
            res_data["general_ledger"] = general_ledger
            # Mapping account data
            accounts_data = res_data["accounts_data"]
            accounts_data = map_type._get_account_data_mapping_afr(
                accounts_data
            )
            res_data["accounts_data"] = accounts_data
        return res_data
