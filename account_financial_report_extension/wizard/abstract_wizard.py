# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AbstractWizard(models.AbstractModel):
    _inherit = "account_financial_report_abstract_wizard"

    map_type_id = fields.Many2one(
        comodel_name="data.map.type",
        help="Used to map data for report printing",
    )

    def _prepare_report_data(self):
        res = super()._prepare_report_aged_partner_balance()
        res.update({"map_type_id": self.map_type_id.id or False})
        return res
