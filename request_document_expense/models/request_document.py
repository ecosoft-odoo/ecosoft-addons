# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    request_type = fields.Selection(
        selection_add=[("expense", "Expense")],
        ondelete={"expense": "cascade"},
    )
    expense_name = fields.Char(
        string="Expense Report Summary",
    )
    expense_line_ids = fields.One2many(
        comodel_name="request.document.expense.line",
        inverse_name="document_id",
    )
    expense_total_amount = fields.Monetary(
        string="Total Amount",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True,
    )
    expense_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        default=lambda self: self.env.user.employee_id,
        check_company=True,
        domain=lambda self: self.env["hr.expense"]._get_employee_id_domain(),
    )
    expense_sheet_ids = fields.One2many(
        comodel_name="hr.expense.sheet",
        inverse_name="request_document_id",
    )

    @api.depends("expense_line_ids.total_amount_company")
    def _compute_amount(self):
        for sheet in self:
            sheet.expense_total_amount = sum(
                sheet.expense_line_ids.mapped("total_amount_company")
            )

    def _get_expense_values(self):
        self.ensure_one()
        expense_list = [
            {
                "name": exp.name,
                "product_id": exp.product_id.id,
                "unit_amount": exp.unit_amount,
                "quantity": exp.quantity,
                "product_uom_id": exp.product_uom_id.id,
                "total_amount": exp.total_amount,
                "currency_id": exp.currency_id.id,
                "tax_ids": [(6, 0, exp.tax_ids.ids)],
                "date": exp.date,
                "employee_id": exp.employee_id.id,
                "payment_mode": exp.payment_mode,
            }
            for exp in self.expense_line_ids
        ]
        return expense_list

    def _get_sheet_values(self, expense_list):
        self.ensure_one()
        return {
            "name": self.expense_name,
            "employee_id": self.expense_employee_id.id,
            "request_document_id": self.id,
            "expense_line_ids": [(0, 0, exp) for exp in expense_list],
        }

    def _update_state_expense(self, sheets):
        self.ensure_one()
        state_config = self.company_id.request_document_ex_state
        if state_config in ["submit", "approve", "post"]:
            sheets.action_submit_sheet()
            if state_config in ["approve", "post"]:
                sheets.approve_expense_sheets()
                if state_config == "post":
                    sheets.action_sheet_move_create()

    def _create_expense(self):
        self.ensure_one()
        # Create Expense Sheet
        expense_list = self._get_expense_values()
        sheet_dict = self._get_sheet_values(expense_list)
        sheets = self.env["hr.expense.sheet"].create(sheet_dict)
        self._update_state_expense(sheets)
        return sheets


class RequestDocumentExpenseLine(models.Model):
    _name = "request.document.expense.line"
    _inherit = "hr.expense"
    _description = "Request Document Expense Line"

    document_id = fields.Many2one(
        comodel_name="request.document",
        required=True,
        ondelete="cascade",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="request_expense_tax",
        column1="document_expense_id",
        column2="tax_id",
        compute="_compute_from_product_id_company_id",
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
        string="Taxes",
    )
