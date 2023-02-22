# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class JournalLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.journal_ledger"

    def _get_data_mapping(self, map_type, in_value):
        for line in map_type.line_ids.filtered(
            lambda l: l.model_id.model == "account.account"
            and l.field_id.name == "code"
        ):
            out_value = line.get_out_value(
                map_type.name, "account.account", "code", in_value
            )
            if out_value:
                out_value = out_value.decode("utf-8")
                s = out_value.index(" ")
                code = out_value[:s]
                name = out_value[s + 1 :]
                return {"code": code, "name": name}
        return False

    def _get_account_data_mapping(self, accounts_data, map_type_id=False):
        """
        accounts_data format is {<id>: <data_dict>} such as
        {1: {'id': 1, 'code': '400000', 'name': 'Income'}}
        """
        if map_type_id:
            map_type = self.env["data.map.type"].browse(map_type_id)
            # Mapping data
            for k, data in accounts_data.items():
                in_value = data["code"]
                data_mapping = self._get_data_mapping(map_type, in_value)
                if data_mapping:
                    data.update(data_mapping)
            return accounts_data

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys():
            # Mapping account data
            account_ids_data = res_data["account_ids_data"]
            account_ids_data = self._get_account_data_mapping(
                account_ids_data, data["map_type_id"]
            )
            res_data["account_ids_data"] = account_ids_data
        return res_data
