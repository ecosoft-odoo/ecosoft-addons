# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class DocType(models.Model):
    _name = "doc.type"
    _description = "For config doctype code that send to INET"
    _rec_name = "name"

    _sql_constraints = [
        (
            "code_uniq_per_doc",
            "UNIQUE(name)",
            "Doc name template must be unique",
        ),
    ]

    name = fields.Char(
        string="Form Name",
        required=True,
    )
    move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("out_invoice_debit", "Customer Debit Note"),
            ("entry", "Customer Payment")
        ],
        string="Type",
    )
    doc_source_template = fields.Selection(
        string="Invoice template source",
        selection=[
            ("odoo", "odoo"),
            ("frappe", "frappe"),
        ],
        default="odoo",
        help="Select source template between Odoo and Frappe",
    )
    doctype_code = fields.Selection(
        selection=[
            # ("380", "380 ใบแจ้งหนี้"),  # We don't use this, not a tax invoice
            ("388", "388 ใบกํากับภาษี"),
            ("T02", "T02 ใบแจ้งหนี้/ใบกํากับภาษี"),
            ("T03", "T03 ใบเสร็จรับเงิน/ใบกํากับภาษี"),
            ("T04", "T04 ใบส่งของ/ใบกํากับภาษี"),
            ("T05", "T05 ใบกํากับภาษี อย่างย่อ"),
            ("T01", "T01 ใบรับ (ใบเสร็จรับเงิน)"),
            ("80", "80 ใบเพิมหนี้"),
            ("81", "81 ใบลดหนี้"),
        ],
        help="""
            380 : ใบแจ้งหนี้,
            388 : ใบกํากับภาษี,
            T02 : ใบแจ้งหนี้/ใบกํากับภาษี,
            T03 : ใบเสร็จรับเงิน/ใบกํากับภาษี,
            T04 : ใบส่งของ/ใบกํากับภาษี,
            T05 : ใบกํากับภาษี อย่างย่อ,
            T01 : ใบรับ (ใบเสร็จรับเงิน),
            80 : ใบเพิมหนี้,
            81 : ใบลดหนี้,
        """,
    )
