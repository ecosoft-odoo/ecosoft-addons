from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def create(self, vals):
        """Helper to fill required po line"""
        for val in vals:
            po_line = self.new(val)
            po_line.onchange_product_id()
            if not val.get("date_planned"):
                val["date_planned"] = po_line.date_planned
            if not val.get("product_uom"):
                val["product_uom"] = po_line.product_uom.id
        return super().create(vals)
