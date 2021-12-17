# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AgedPartnerBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.abstract_report"

    def _get_report_data_mapping(
        self, report_data, map_type_id=False, merge_data=False
    ):
        if map_type_id:
            if not merge_data:
                merge_data = []
            map_type = self.env["data.map.type"].browse(map_type_id)
            unwanted = []
            report_data_merge = {}
            # Mapping data
            for i, data in enumerate(report_data):
                in_value = data["code"]
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
                        data.update({"code": code, "name": name})
                        if code in report_data_merge.keys():
                            for k in merge_data:
                                report_data_merge[code][k] += data[k]
                            unwanted.append(i)
                        else:
                            merge_data_dict = {}
                            for k in merge_data:
                                merge_data_dict[k] = data[k]
                            report_data_merge[code] = merge_data_dict
                        break
            # Delete unwanted data
            for ele in sorted(unwanted, reverse=True):
                del report_data[ele]
            # Update report data
            for data in report_data:
                code = data["code"]
                if code in report_data_merge.keys():
                    for k in merge_data:
                        data[k] = report_data_merge[code][k]
        return report_data
