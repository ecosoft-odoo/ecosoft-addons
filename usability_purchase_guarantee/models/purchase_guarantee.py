# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class PurchaseGuarantee(models.Model):
    _name = "purchase.guarantee"
    _inherit = ["analytic.dimension.line", "purchase.guarantee"]
    _analytic_tag_field_name = "analytic_tag_ids"
    _budget_analytic_field = "analytic_account_id"

    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        domain="[('id', 'in', fund_all)]",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
    )

    @api.depends("analytic_account_id")
    def _compute_fund_all(self):
        for rec in self:
            origin = False
            if rec.reference:
                if rec.reference._name == "purchase.requisition":
                    origin = rec.reference.line_ids
                elif rec.reference._name == "purchase.order":
                    origin = rec.reference.order_line
            rec.fund_all = origin.mapped("fund_id") if origin else origin

    @api.depends("analytic_account_id")
    def _compute_analytic_tag_all(self):
        for doc in self:
            analytic_tag_ids = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped("analytic_tag_ids")
            doc.analytic_tag_all = analytic_tag_ids

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [x for x in self.fields_get().keys() if x.startswith("x_dimension_")]

    @api.onchange("analytic_tag_all")
    def _onchange_analytic_tag_all(self):
        dimension_fields = self._get_dimension_fields()
        analytic_tag_ids = self[self._budget_analytic_field].allocation_line_ids.mapped(
            "analytic_tag_ids"
        )
        if not analytic_tag_ids:
            self.analytic_tag_ids = False
            return
        if (
            len(analytic_tag_ids) != len(dimension_fields)
            and self[self._analytic_tag_field_name]
        ):
            return
        self[self._analytic_tag_field_name] = (
            len(analytic_tag_ids) == len(dimension_fields) and analytic_tag_ids or False
        )

    @api.onchange("fund_all")
    def _onchange_fund_all(self):
        for rec in self:
            rec.fund_id = rec.fund_all._origin.id if len(rec.fund_all) == 1 else False
