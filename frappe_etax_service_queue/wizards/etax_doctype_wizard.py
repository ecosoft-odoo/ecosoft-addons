# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ETaxDoctypeWizard(models.TransientModel):
    _inherit = "etax.doctype.wizard"

    run_background = fields.Boolean()

    def _sign_etax(self, moves):
        if self.run_background:
            moves.write({"etax_status": "processing"})
            return self.with_delay()._process_sign_etax(moves)
        return super()._sign_etax(moves)
