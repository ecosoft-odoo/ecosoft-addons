# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
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
    tester_move_id = fields.Many2one(
        comodel_name="stock.move", readonly=True, check_company=True, copy=False
    )
    tester_product_id = fields.Many2one(
        comodel_name="product.product",
        domain="[('type', 'in', ['product', 'consu']),"
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={"done": [("readonly", True)]},
        check_company=True,
    )
    tester_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Tester Lot/Serial",
        states={"done": [("readonly", True)]},
        domain="[('product_id', '=', tester_product_id), ('company_id', '=', company_id)]",
        check_company=True,
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

    def action_get_stock_move_lines(self):
        action = super().action_get_stock_move_lines()
        action["domain"] = [
            ("move_id", "in", [self.tester_move_id.id, self.move_id.id])
        ]
        return action

    def _prepare_tester_move_values(self):
        self.ensure_one()
        return {
            "name": self.name,
            "origin": self.origin or self.picking_id.name or self.name,
            "company_id": self.company_id.id,
            "product_id": self.tester_product_id.id,
            "product_uom": self.product_uom_id.id,
            "state": "draft",
            "product_uom_qty": self.scrap_qty,
            "location_id": self.scrap_location_id.id,
            "scrapped": True,
            "origin_returned_move_id": self.move_id.id,  # get price unit from origin
            "location_dest_id": self.location_id.id,
            "move_line_ids": [
                Command.create(
                    {
                        "product_id": self.tester_product_id.id,
                        "product_uom_id": self.product_uom_id.id,
                        "qty_done": self.scrap_qty,
                        "location_id": self.scrap_location_id.id,
                        "location_dest_id": self.location_id.id,
                        "package_id": self.package_id.id,
                        "owner_id": self.owner_id.id,
                        "lot_id": self.tester_lot_id.id,
                    }
                )
            ],
            "picking_id": self.picking_id.id,
        }

    def do_scrap(self):
        """This function will create new journal entry, if checked tester"""
        res = super().do_scrap()
        self = self.sudo()
        move_template = self.env["account.move.template.run"]
        stock_valuation = self.env["stock.valuation.layer"]
        for scrap in self:
            if not scrap.is_tester:
                continue

            # Create reverse move
            move = self.env["stock.move"].create(scrap._prepare_tester_move_values())
            move.with_context(is_scrap=True)._action_done()
            scrap.write({"tester_move_id": move.id, "state": "done"})
            scrap.date_done = fields.Datetime.now()

            # Create account move
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
