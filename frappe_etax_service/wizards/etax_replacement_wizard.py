# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EtaxReplacementWizard(models.TransientModel):
    _name = "etax.replacement.wizard"
    _description = "Select etax replacement document on wizard"

    purpose_code_id = fields.Many2one(
        comodel_name="etax.purpose.code",
        string="Purpose",
    )
    reason = fields.Char(
        required=True,
    )
    origin_ref = fields.Reference(
        selection=[
            ("account.move", "Invoices"),
            ("account.payment", "Payments"),
        ],
        string="Origin",
    )
    etax_doctype_code = fields.Char(string="Doctype Code")

    @api.onchange("purpose_code_id")
    def _onchange_purpose_code_id(self):
        self.reason = self.purpose_code_id.reason

    def create_replacement(self):
        origin_ref = self.origin_ref
        origin_ref.ensure_one()

        if origin_ref._name == "account.move":
            invoice_date = origin_ref.invoice_date
        elif origin_ref._name == "account.payment":
            invoice_date = origin_ref.date

        self._check_replacement_lock_date(invoice_date)

        replacement = origin_ref.create_replacement_etax()
        # Update replacement document
        replacement.write(
            {
                "create_purpose_code": self.purpose_code_id.code,
                "create_purpose": self.reason,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": replacement._name,
            "res_id": replacement.id,
            "context": self.env.context,
        }

    def _check_replacement_lock_date(self, invoice_date):
        # Test lock date
        lock_date = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("frappe_etax_service.replacement_lock_date", 1)
        )
        dt = (invoice_date.replace(day=1) + datetime.timedelta(days=32)).replace(
            day=lock_date
        )
        if datetime.date.today() > dt:
            raise ValidationError(
                self.env._("Create Replace e-Tax not allowed after %s")
                % dt.strftime("%d/%m/%Y")
            )
