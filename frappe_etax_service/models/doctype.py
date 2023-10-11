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

    name = fields.Char(required=True)
    report_template_id = fields.Many2one(
        string="Invoice template",
        comodel_name="ir.actions.report",
        domain=[("model", "=", "account.move"), ("binding_model_id", "!=", False)],
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
            ("380", "380"),
            ("388", "388"),
            ("T02", "T02"),
            ("T03", "T03"),
            ("T04", "T04"),
            ("T05", "T05"),
            ("T01", "T01"),
            ("80", "80"),
            ("81", "81"),
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
