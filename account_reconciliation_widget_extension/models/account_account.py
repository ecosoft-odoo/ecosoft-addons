# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAccountType(models.Model):
    _inherit = "account.account.type"

    skip_synchronization_reconcile_widget = fields.Boolean(
        string="Reconcile Widget - skip synchronization",
        help="If check, it will 'skip_account_move_synchronization' when reconcile widget.",
    )
