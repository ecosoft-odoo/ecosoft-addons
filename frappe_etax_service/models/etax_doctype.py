# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ETaxDocType(models.Model):
    _name = "etax.doctype"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "For config doctype code that send to INET"

    name = fields.Char(
        string="Form Name",
        tracking=True,
    )
    report_id = fields.Many2one(
        comodel_name="ir.actions.report",
    )
    move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("out_invoice_debit", "Customer Debit Note"),
            ("entry", "Customer Payment"),
        ],
        string="Type",
        tracking=True,
    )
    doc_source_template = fields.Selection(
        string="Invoice template source",
        selection=[
            ("odoo", "odoo"),
            ("frappe", "frappe"),
        ],
        default="odoo",
        help="Select source template between Odoo and Frappe",
        tracking=True,
    )
    doctype_code_id = fields.Many2one(
        comodel_name="etax.doctype.code",
        string="Document Type Code",
        tracking=True,
    )

    _sql_constraints = [
        (
            "code_uniq_per_doc",
            "UNIQUE(name)",
            "Form name must be unique",
        ),
    ]
