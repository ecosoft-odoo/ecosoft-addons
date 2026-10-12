# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    request_document_id = fields.Many2one(
        comodel_name="request.document",
        copy=False,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    _sql_constraints = [
        (
            "request_document_unique",
            "unique(request_document_id)",
            "Only one Vendor Bill can be linked to a Request Document.",
        ),
    ]

    @api.constrains("request_document_id", "move_type", "company_id")
    def _check_request_document(self):
        for rec in self.filtered("request_document_id"):
            request = rec.request_document_id
            if rec.move_type != "in_invoice" or request.request_type != "vendor_bill":
                raise ValidationError(
                    self.env._(
                        "Only Vendor Bills can be linked to Vendor Bill requests."
                    )
                )
            if rec.company_id != request.company_id:
                raise ValidationError(
                    self.env._("The bill and request must belong to the same company.")
                )

    def _check_request_editable(self):
        for rec in self:
            if rec.request_document_id and rec.request_document_id.state not in (
                "draft",
                "done",
            ):
                raise UserError(
                    self.env._(
                        "You cannot modify a bill while its request "
                        "is awaiting completion."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves.filtered("request_document_id"):
            if move.request_document_id.state != "draft" or move.state != "draft":
                raise UserError(
                    self.env._(
                        "Bills can only be linked while both bill "
                        "and request are in Draft."
                    )
                )
        return moves

    def write(self, vals):
        self._check_request_editable()
        if "request_document_id" in vals:
            request = self.env["request.document"].browse(vals["request_document_id"])
            for move in self:
                if move.request_document_id.id == vals["request_document_id"]:
                    continue
                if (
                    move.state != "draft"
                    or (
                        move.request_document_id
                        and move.request_document_id.state != "draft"
                    )
                    or (request and request.state != "draft")
                ):
                    raise UserError(
                        self.env._("Bills can only be linked or unlinked in Draft.")
                    )
        return super().write(vals)

    def unlink(self):
        self._check_request_editable()
        return super().unlink()

    def _post(self, soft=True):
        for move in self:
            if move.request_document_id and move.request_document_id.state != "done":
                raise UserError(
                    self.env._("Complete the request before posting its Vendor Bill.")
                )
        return super()._post(soft=soft)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        self.env["account.move"].browse(
            [vals["move_id"] for vals in vals_list if vals.get("move_id")]
        )._check_request_editable()
        return super().create(vals_list)

    def write(self, vals):
        self.move_id._check_request_editable()
        if vals.get("move_id"):
            self.env["account.move"].browse(vals["move_id"])._check_request_editable()
        return super().write(vals)

    def unlink(self):
        self.move_id._check_request_editable()
        return super().unlink()
