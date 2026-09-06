# Copyright 2026 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    adjustment_notes = env["account.move"].search(
        [
            "|",
            ("move_type", "in", ("out_refund", "out_invoice_debit")),
            "&",
            ("move_type", "=", "out_invoice"),
            ("debit_origin_id", "!=", False),
        ]
    )
    env.add_to_compute(adjustment_notes._fields["enable_etax"], adjustment_notes)
    adjustment_notes._recompute_recordset(["enable_etax"])
