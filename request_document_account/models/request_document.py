# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class RequestDocument(models.Model):
    _inherit = "request.document"

    move_ids = fields.One2many(
        "account.move", "request_document_id", string="Vendor Bills"
    )

    def unlink(self):
        if self.move_ids:
            raise UserError(
                self.env._(
                    "Delete or unlink the Vendor Bill before deleting its request line."
                )
            )
        return super().unlink()

    def write(self, vals):
        protected = {"request_type", "request_id", "currency_id"}.intersection(vals)
        for rec in self.filtered("move_ids") if protected else self.browse():
            for field in protected:
                current = rec[field] if field == "request_type" else rec[field].id
                if vals[field] != current:
                    raise UserError(
                        self.env._(
                            "Unlink the bill before changing its request "
                            "type, currency or parent."
                        )
                    )
        return super().write(vals)

    @api.model
    def _get_request_type_selection(self):
        return super()._get_request_type_selection() + [("vendor_bill", "Vendor Bill")]

    @api.depends(
        "move_ids", "move_ids.name", "move_ids.ref", "move_ids.amount_total_signed"
    )
    def _compute_document(self):
        res = super()._compute_document()
        for rec in self.filtered(lambda line: line.request_type == "vendor_bill"):
            bill = rec.move_ids
            rec.name_document = (bill.ref or bill.name or "") if bill else ""
            # Vendor bills have a negative signed total, in company currency.
            rec.total_amount_document = -bill.amount_total_signed if bill else 0.0
        return res

    def _check_vendor_bill(self):
        for rec in self.filtered(lambda line: line.request_type == "vendor_bill"):
            if len(rec.move_ids) != 1 or rec.move_ids.state != "draft":
                raise UserError(
                    self.env._("Each Vendor Bill request must have one draft bill.")
                )
            if rec.currency_id != rec.company_id.currency_id:
                raise UserError(
                    self.env._("Vendor Bill requests must use the company currency.")
                )

    def _create_vendor_bill(self):
        self.ensure_one()
        self._check_vendor_bill()
        # Posting is performed by request.order after the request reaches Done.

    def open_request_document(self):
        self.ensure_one()
        if self.request_type != "vendor_bill":
            return super().open_request_document()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Vendor Bill"),
            "res_model": "account.move",
            "view_mode": "form",
            "views": [(self.env.ref("account.view_move_form").id, "form")],
            "res_id": self.move_ids.id or False,
            "context": dict(
                self.env.context,
                default_move_type="in_invoice",
                default_company_id=self.company_id.id,
                default_request_document_id=self.id,
            ),
        }
