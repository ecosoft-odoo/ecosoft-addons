# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def update_account_hooks(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Update Not Affect Budget = True in sale journals
        sale_journals = env["account.journal"].search([("type", "=", "sale")])
        for sale_journal in sale_journals:
            sale_journal.update({"not_affect_budget": True})
