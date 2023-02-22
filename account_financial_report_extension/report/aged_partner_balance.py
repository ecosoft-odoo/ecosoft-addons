# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AgedPartnerBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.aged_partner_balance"

    def _get_report_values(self, docids, data):
        res_data = super()._get_report_values(docids, data)
        if "map_type_id" in data.keys() and data["map_type_id"]:
            map_type = self.env["data.map.type"].browse(data["map_type_id"])
            # Mapping report data
            aged_partner_balance = res_data["aged_partner_balance"]
            aged_partner_balance = map_type._get_report_data_mapping_afr(
                aged_partner_balance
            )
            res_data["aged_partner_balance"] = aged_partner_balance
        return res_data
