# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, models


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        procurement_groups = [
            "hii_user_role.group_role_procurement_officer",
            "hii_user_role.group_role_procurement_head",
        ]
        if not any([self.env.user.has_group(pg) for pg in procurement_groups]):
            if view_type in ["form", "tree"]:
                doc = etree.XML(res["arch"])
                nodes = doc.xpath("//{view_type}".format(view_type=view_type))
                for node in nodes:
                    node.set("create", "false")
                    node.set("edit", "false")
                    node.set("delete", "false")
                res["arch"] = etree.tostring(doc)
        return res
