# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "etax.th"]

    has_create_replacement = fields.Boolean(
        copy=False,
        default=False,
    )

    def action_open_replacement_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Create Replacement",
            "res_model": "wizard.select.replacement.purpose",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
            },
        }

    def action_draft(self):
        if (
            self.filtered(
                lambda pay: pay.etax_status in ("success", "processing", "to_process")
            )
            and not self.has_create_replacement
            and not self._context.get("force_reset", False)
        ):
            raise ValidationError(
                _(
                    "Cannot reset to draft, eTax submission already started "
                    "or succeeded.\n"
                    "You should do the refund process instead."
                )
            )
        return super().action_draft()

    def _get_branch_id(self):
        """
        By default, core odoo do not provide branch_id field in
        account.move and account.payment.
        This method will check if branch_id is exist in model and return branch_id
        """
        if self.reconciled_invoice_ids:
            if "branch_id" in self.env["account.move"]._fields:
                return self.reconciled_invoice_ids[0].branch_id.name
        else:
            return False

    def create_replacement_etax(self):
        """
        Create replacement receipt eTax
        """
        self.ensure_one()
        if not (self.state == "posted" and self.etax_status == "success"):
            raise ValidationError(_("Only posted etax payment can have a substitution"))
        if len(self.reconciled_invoice_ids) > 1:
            raise ValidationError(_("Multiple reconciled invoices not allowed"))
        res = self.with_context(include_business_fields=True).copy_data()
        old_number = self.name
        res[0]["posted_before"] = self.posted_before
        res[0]["date"] = self.date
        res[0]["ref"] = self.ref
        res[0]["doc_name_template"] = self.doc_name_template.id
        payment = self.create(res[0])
        self.has_create_replacement = True
        self.action_draft()
        self.action_cancel()
        self.name = old_number  # Ensure name.
        return payment
