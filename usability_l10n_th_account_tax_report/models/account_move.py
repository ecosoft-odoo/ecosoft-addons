# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)


from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def create_wht_cert(self):
        # Pass check Type of Income.
        # Check Type of Income when done withholding tax cert.
        try:
            super().create_wht_cert()
        except UserError:
            certs = self._preapare_wht_certs()
            self.env["withholding.tax.cert"].create(certs)
