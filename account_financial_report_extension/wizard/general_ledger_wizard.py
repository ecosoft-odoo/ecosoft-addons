# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class GeneralLedgerReportWizard(models.TransientModel):
    _inherit = "general.ledger.report.wizard"

    map_type_id = fields.Many2one(
        comodel_name="data.map.type",
        string="Map Type",
        help="Used to map data for report printing",
    )

    def _prepare_report_general_ledger(self):
        res = super()._prepare_report_general_ledger()
        res.update({"map_type_id": self.map_type_id.id or False})
        return res
