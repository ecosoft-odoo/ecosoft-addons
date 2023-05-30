# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class JournalLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.journal_ledger"

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys() and data["map_type_id"]:
            map_type = self.env["data.map.type"].browse(data["map_type_id"])
            # Mapping account data
            account_ids_data = res_data["account_ids_data"]
            account_ids_data = map_type._get_account_data_mapping_afr(account_ids_data)
            res_data["account_ids_data"] = account_ids_data
        return res_data
