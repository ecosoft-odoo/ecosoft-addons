# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountFinancialReport(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"
    _rec_name = "name"

    name = fields.Char(
        string="Report Name",
        required=True,
        translate=True,
    )
    parent_id = fields.Many2one(
        comodel_name="account.financial.report",
        string="Parent",
    )
    children_ids = fields.One2many(
        comodel_name="account.financial.report",
        inverse_name="parent_id",
        string="Account Report",
    )
    sequence = fields.Integer(
        string="Sequence",
    )
    level = fields.Integer(
        compute="_compute_level",
        string="Level",
        store=True,
    )
    type = fields.Selection(
        selection=[
            ("sum", "View"),
            ("accounts", "Accounts"),
            ("account_type", "Account Type"),
            ("account_report", "Report Value"),
        ],
        string="Type",
        default="sum",
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="account_account_financial_report",
        column1="report_line_id",
        column2="account_id",
        string="Accounts",
    )
    account_report_id = fields.Many2one(
        comodel_name="account.financial.report",
        string="Report Value",
    )
    account_type_ids = fields.Many2many(
        comodel_name="account.account.type",
        relation="account_account_financial_report_type",
        column1="report_id",
        column2="account_type_id",
        string="Account Types",
    )
    sign = fields.Selection(
        selection=[
            ("-1", "Reverse balance sign"),
            ("1", "Preserve balance sign"),
        ],
        string="Sign on Reports",
        required=True,
        default="1",
        help="For accounts that are typically more"
        " debited than credited and that you"
        " would like to print as negative"
        " amounts in your reports, you should"
        " reverse the sign of the balance;"
        " e.g.: Expense account. The same applies"
        " for accounts that are typically more"
        " credited than debited and that you would"
        " like to print as positive amounts in"
        " your reports; e.g.: Income account.",
    )
    display_detail = fields.Selection(
        selection=[
            ("no_detail", "No detail"),
            ("detail_flat", "Display children flat"),
            ("detail_with_hierarchy", "Display children with hierarchy"),
        ],
        string="Display details",
        default="detail_flat",
    )
    style_overwrite = fields.Selection(
        selection=[
            ("0", "Automatic formatting"),
            ("1", "Main Title 1 (bold, underlined)"),
            ("2", "Title 2 (bold)"),
            ("3", "Title 3 (bold, smaller)"),
            ("4", "Normal Text"),
            ("5", "Italic Text (smaller)"),
            ("6", "Smallest Text"),
        ],
        string="Financial Report Style",
        default="0",
        help="You can set up here the format you want this"
        " record to be displayed. If you leave the"
        " automatic formatting, it will be computed"
        " based on the financial reports hierarchy "
        "(auto-computed field 'level').",
    )

    @api.depends("parent_id", "parent_id.level")
    def _compute_level(self):
        """Returns a dictionary with key=the ID of a record and
        value = the level of this
          record in the tree structure."""
        for report in self:
            level = 0
            if report.parent_id:
                level = report.parent_id.level + 1
            report.level = level

    def _get_children_by_order(self):
        """returns a recordset of all the children computed recursively,
        and sorted by sequence. Ready for the printing"""
        res = self
        children = self.search([("parent_id", "in", self.ids)], order="sequence ASC")
        if children:
            for child in children:
                res += child._get_children_by_order()
        return res
