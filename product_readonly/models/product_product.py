# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )
        # if user has group product verify, noting to do
        product_verify_group = self.env.user.has_group(
            "product_template_readonly.group_product_verify"
        )
        if product_verify_group:
            return res
        # Hide button create/edit in product view
        doc = etree.XML(res["arch"])
        nodes = []
        if view_type == "tree":
            nodes = doc.xpath("//tree")
        elif view_type == "form":
            nodes = doc.xpath("//form")
        for node in nodes:
            node.set("create", "false")
            node.set("edit", "false")
        res["arch"] = etree.tostring(doc)
        return res
