# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
import calendar
import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import format_date


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
