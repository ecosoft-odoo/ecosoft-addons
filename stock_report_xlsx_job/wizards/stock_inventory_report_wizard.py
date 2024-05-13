# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)


from odoo import models


class StockInventoryReportWizard(models.TransientModel):
    _inherit = "stock.inventory.report.wizard"

    def button_export_xlsx_with_job(self):
        """Used queue job for export excel to report_async (active_id=1)"""
        report_name = "stock_report_xlsx.report_stock_inventory_xlsx"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", "xlsx")],
                limit=1,
            )
            .with_context(async_process=True, active_id=1)
            .report_action(self, config=False)
        )
