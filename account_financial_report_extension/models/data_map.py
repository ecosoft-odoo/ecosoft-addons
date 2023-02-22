# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DataMapType(models.Model):
    _inherit = "data.map.type"

    model = fields.Selection(
        selection_add=[
            ("aged_partner_balance", "Aged Partner Balance"),
            ("general_ledger", "General Ledger"),
            ("journal_ledger", "Journal Ledger"),
            ("open_items", "Open Items"),
            ("trial_balance", "Trial Balance"),
        ],
        ondelete={
            "aged_partner_balance": "cascade",
            "general_ledger": "cascade",
            "journal_ledger": "cascade",
            "open_items": "cascade",
            "trial_balance": "cascade",
        },
    )

    def _get_data_mapping_afr(self, in_value):
        self.ensure_one()
        for line in self.line_ids.filtered(
            lambda l: l.model_id.model == "account.account"
            and l.field_id.name == "code"
        ):
            out_value = line.get_out_value(
                self.name, "account.account", "code", in_value
            )
            if out_value:
                out_value = out_value.decode("utf-8")
                s = out_value.index(" ")
                code = out_value[:s]
                name = out_value[s + 1 :]
                return {"code": code, "name": name}
        return False

    def _get_report_data_mapping_afr(self, report_data):
        """
        report_data format is [<data_dict>, <data_dict>] such as
        [{'code': '400000', 'name': 'Income'}, {'code': '600000', 'name': 'Expense'}]
        """
        # Mapping data
        for i, data in enumerate(report_data):
            in_value = data["code"]
            data_mapping = self._get_data_mapping_afr(in_value)
            if data_mapping:
                data.update(data_mapping)
        return report_data

    def _get_account_data_mapping_afr(self, accounts_data):
        """
        accounts_data format is {<id>: <data_dict>} such as
        {1: {'id': 1, 'code': '400000', 'name': 'Income'}}
        """
        # Mapping data
        for k, data in accounts_data.items():
            in_value = data["code"]
            data_mapping = self._get_data_mapping_afr(in_value)
            if data_mapping:
                data.update(data_mapping)
        return accounts_data
