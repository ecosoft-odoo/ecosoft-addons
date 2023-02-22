# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OpenItemsReport(models.AbstractModel):
    _inherit = "report.account_financial_report.open_items"

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys():
            map_type = self.env["data.map.type"].browse(data["map_type_id"])
            # Mapping report data
            AccountAccount = self.env["account.account"]
            Open_Items = res_data["Open_Items"]
            for account_id in Open_Items.keys():
                account = AccountAccount.browse(account_id)
                in_value = account.code
                data_mapping = self._get_data_mapping(map_type, in_value)
                if data_mapping:
                    for partner_id in Open_Items[account_id].keys():
                        for line in Open_Items[account_id][partner_id]:
                            line.update({"account_id": (account_id, " ".join([data_mapping["code"], data_mapping["name"]]))})
            res_data["Open_Items"] = Open_Items
            # Mapping account data
            accounts_data = res_data["accounts_data"]
            accounts_data = self._get_account_data_mapping(
                accounts_data, data["map_type_id"]
            )
            res_data["accounts_data"] = accounts_data
        return res_data
