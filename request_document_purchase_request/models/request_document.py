# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    request_type = fields.Selection(
        selection_add=[("purchase_request", "Purchase Request")],
        ondelete={"purchase_request": "cascade"},
    )

    pr_requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested By",
        check_company=True,
        default=lambda self: self.env.user,
    )
    pr_description = fields.Text(string="Description")
    pr_origin = fields.Char(string="Source Document")
    pr_date_start = fields.Date(
        string="Creation date",
        default=fields.Date.context_today,
    )
    pr_picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        default=lambda self: self._default_picking_type(),
    )
    pr_estimated_cost = fields.Monetary(
        compute="_compute_estimated_cost",
        string="Total Estimated Cost",
        store=True,
    )
    pr_line_ids = fields.One2many(
        comodel_name="request.document.purchase.request.line",
        inverse_name="document_id",
    )
    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="request_document_id",
    )

    @api.depends("pr_line_ids", "pr_line_ids.estimated_cost")
    def _compute_estimated_cost(self):
        for rec in self:
            rec.pr_estimated_cost = sum(rec.pr_line_ids.mapped("estimated_cost"))

    @api.model
    def _default_picking_type(self):
        type_obj = self.env["stock.picking.type"]
        company_id = self.env.context.get("company_id") or self.env.company.id
        types = type_obj.search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not types:
            types = type_obj.search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)]
            )
        return types[:1]

    def _get_pr_line_values(self):
        self.ensure_one()
        pr_line_list = [
            {
                "name": line.name,
                "product_id": line.product_id.id,
                "product_qty": line.product_qty,
                "date_required": line.date_required,
                "estimated_cost": line.estimated_cost,
            }
            for line in self.pr_line_ids
        ]
        return pr_line_list

    def _get_pr_values(self, pr_line_list):
        self.ensure_one()
        return {
            "name": "New",
            "requested_by": self.pr_requested_by.id,
            "origin": self.pr_origin,
            "description": self.pr_description,
            "date_start": self.pr_date_start,
            "picking_type_id": self.pr_picking_type_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "request_document_id": self.id,
            "line_ids": [(0, 0, line) for line in pr_line_list],
        }

    def _update_state_purchase_request(self, purchase_request):
        self.ensure_one()
        state_config = self.company_id.request_document_pr_state
        if state_config in ["to_approve", "approved", "done"]:
            purchase_request.button_to_approve()
            if state_config in ["approved", "done"]:
                purchase_request.button_approved()
                if state_config == "done":
                    purchase_request.button_done()
        if state_config == "rejected":
            purchase_request.button_rejected()

    def _create_purchase_request(self):
        self.ensure_one()
        # Create Purchase Request
        pr_line_list = self._get_pr_line_values()
        sheet_dict = self._get_pr_values(pr_line_list)
        purchase_request = self.env["purchase.request"].create(sheet_dict)
        self._update_state_purchase_request(purchase_request)
        return purchase_request


class RequestDocumentPurchaseRequestLine(models.Model):
    _name = "request.document.purchase.request.line"
    _inherit = "purchase.request.line"
    _description = "Purchase Request Line"

    document_id = fields.Many2one(
        comodel_name="request.document",
        string="Document",
        ondelete="cascade",
    )
    purchase_lines = fields.Many2many(
        comodel_name="purchase.order.line",
        relation="document_pr_po_line_rel",
        column1="document_id",
        column2="purchase_order_line_id",
    )
