# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ETaxDoctypeWizard(models.TransientModel):
    _name = "etax.doctype.wizard"
    _description = "Select eTax Document Type"

    etax_doctype_id = fields.Many2one(
        comodel_name="etax.doctype",
        string="eTax Document Type",
    )
    etax_doctype_locked = fields.Boolean(default=False)
    move_type = fields.Selection(
        selection=[
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("out_invoice_debit", "Customer Debit Note"),
            ("entry", "Customer Payment"),
        ],
        string="Type",
    )

    def _process_sign_etax(self, moves):
        moves.write(
            {
                "etax_doctype_id": self.etax_doctype_id.id,
                "is_send_frappe": True,
            }
        )
        for move in moves:
            move.action_call_api(move._etax_sign_api_code)

    def _sign_etax(self, moves):
        """Hooks for extending the sign_etax method"""
        self._process_sign_etax(moves)

    def sign_etax_invoice(self):
        res_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", False)
        objects = self.env[res_model].browse(active_ids)
        objects._pre_etax_validate()
        return self._sign_etax(objects)
