# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "etax.service.mixin"]

    _etax_sign_api_code = "FRAPPE_ETAX_PAYMENT_SIGN"
    _etax_replace_api_code = "FRAPPE_ETAX_PAYMENT_REPLACE"

    has_create_replacement = fields.Boolean(
        copy=False,
        default=False,
    )
    replaced_receipt_id = fields.Many2one(
        comodel_name="account.payment",
        string="Replaced Receipt Payment Document",
        readonly=True,
        copy=False,
        help="This field support replacement payment",
    )

    def _hook_update_data(self, code_api, result):
        res = super()._hook_update_data(code_api, result)
        if code_api == self._etax_sign_api_code and self.etax_status == "success":
            if self.replaced_receipt_id:
                self.replaced_receipt_id.etax_status = "replace"
        return res

    def action_draft(self):
        if (
            self.filtered(
                lambda pay: pay.etax_status in ("success", "processing", "to_process")
            )
            and not self.has_create_replacement
            and not self.env.context.get("force_reset", False)
        ):
            raise ValidationError(
                self.env._(
                    "Cannot reset to draft, eTax submission already started "
                    "or succeeded.\n"
                    "You should do the refund process instead."
                )
            )
        return super().action_draft()

    def _prepare_context_for_wizard(self, **kwargs):
        move_type = list(set(self.move_id.mapped("move_type")))
        if len(move_type) > 1:
            raise UserError(self.env._("Please select only one type"))
        kwargs.update(
            {
                "default_move_type": move_type[0],
                # NOTE: Ensure active_model is payment,
                # because when click e-Tax Invoice from Invoice > Payment,
                # active_model will send with account.move
                "active_model": "account.payment",
                "active_ids": self.ids,
                "active_id": self.id,
            }
        )
        if self.replaced_receipt_id and self.etax_doctype_id:
            kwargs.update(
                {
                    "default_etax_doctype_id": self.etax_doctype_id.id,
                    "default_etax_doctype_locked": True,
                }
            )
        return super()._prepare_context_for_wizard(**kwargs)

    def action_open_replacement_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Create Replacement"),
            "res_model": "etax.replacement.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_etax_doctype_code": self.etax_doctype_code,
                "default_origin_ref": f"{self._name},{self.id}",
            },
        }

    def create_replacement_etax(self):
        """Create replacement receipt eTax"""
        self.ensure_one()
        if not (self.state == "paid" and self.etax_status == "success"):
            raise ValidationError(
                self.env._("Only posted etax payment can have a substitution")
            )
        if len(self.reconciled_invoice_ids) > 1:
            raise ValidationError(
                self.env._("Multiple reconciled invoices not allowed")
            )
        res = self.with_context(include_business_fields=True).copy_data()[0]

        # Preserve important fields manually
        res.update(
            {
                "date": self.date,
                "etax_doctype_id": self.etax_doctype_id.id,
                "replaced_receipt_id": self.id,
            }
        )

        payment = self.create(res)
        self.has_create_replacement = True
        self.action_cancel()
        return payment
