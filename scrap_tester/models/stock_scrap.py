# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tests.common import Form


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    enable_scrap_tester = fields.Boolean(
        compute="_compute_enable_scrap_tester",
        store=True,
    )
    is_tester = fields.Boolean(
        string="Tester",
    )
    move_from_template_id = fields.Many2one(
        comodel_name="account.move",
        readonly=True,
        copy=False,
    )

    @api.depends("company_id")
    def _compute_enable_scrap_tester(self):
        for rec in self:
            rec.enable_scrap_tester = rec.company_id.enable_scrap_tester

    @api.onchange("is_tester")
    def _onchange_scrap_tester(self):
        self.scrap_location_id = self._get_default_scrap_location_id()
        if self.is_tester:
            self.scrap_location_id = self.company_id.scrap_tester_location_default.id

    def do_scrap(self):
        """This function will create new journal entry, if checked tester"""
        res = super().do_scrap()
        move_template = self.env["account.move.template.run"]
        stock_valuation = self.env["stock.valuation.layer"]
        for scrap in self:
            if not scrap.is_tester:
                continue
            sv = stock_valuation.search([("stock_move_id", "=", scrap.move_id.id)])
            with Form(move_template) as f:
                f.template_id = scrap.company_id.scrap_account_template_default
            template_run = f.save()
            template_run.load_lines()
            template_run.line_ids.write({"amount": abs(sv.value)})
            res_template = template_run.with_context(scrap_id=scrap.id).generate_move()
            scrap.move_from_template_id = res_template["res_id"]
            if scrap.company_id.scrap_move_state == "posted":
                scrap.move_from_template_id.action_post()
        return res
