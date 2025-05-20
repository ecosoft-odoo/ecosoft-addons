# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestRequestDocumentExpense(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]
        cls.request_model = cls.env["request.order"]
        cls.expense = cls.create_expense(cls)

    def test_01_process_request_expense(self):
        # Create request order and line
        request_order = self.request_model.create(
            {"line_ids": [Command.create({"request_type": "expense"})]}
        )
        request_expense = request_order.line_ids
        # Create sheet and link to request
        expense_sheet = self.expense_sheet_model.create(
            {
                "name": "Test Expense Sheet",
                "employee_id": self.expense_employee.id,
                "request_document_id": request_expense.id,
                "expense_line_ids": [Command.link(self.expense.id)],
            }
        )
        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_expense.expense_sheet_ids), 1)
        self.assertEqual(request_order.expense_sheet_counts, 1)

        # Check edit expense related request. it shouldn't editable
        error_msg = (
            "You cannot modify this record because the related "
            "Request Document is not in 'Done' state."
        )
        with self.assertRaisesRegex(UserError, error_msg):
            expense_sheet.name = "NEW TEST EXPENSE"

        # Allow edit if send context `allow_edit`
        expense_sheet.with_context(allow_edit=1).name = "NEW TEST EXPENSE"

        self.assertEqual(request_expense.name_document, expense_sheet.name)
        # Open details, it should open expense sheet
        action = request_expense.open_request_document()
        self.assertEqual(action["res_model"], "hr.expense.sheet")
        self.assertEqual(action["res_id"], expense_sheet.id)

        request_order.company_id.request_document_ex_state = "post"
        request_order.action_submit()
        self.assertEqual(request_order.state, "submit")
        request_order.action_approve()
        self.assertEqual(request_order.state, "approve")
        self.assertEqual(expense_sheet.state, "draft")
        request_order.action_process_document()
        self.assertEqual(request_order.state, "done")
        self.assertEqual(expense_sheet.state, "post")

        # Check change value sheet after request done. it should do it.
        expense_sheet.name = "TEST CHANGE NAME AFTER REQUEST DONE"

        # Check open expense sheet from smart button
        action = request_order.action_open_expense_sheet()
        self.assertEqual(action["res_model"], "hr.expense.sheet")
        self.assertEqual(action["domain"][0][2], [expense_sheet.id])

    def test_02_delete_request_expense(self):
        # Create request order and line
        request_order = self.request_model.create(
            {"line_ids": [Command.create({"request_type": "expense"})]}
        )
        request_expense = request_order.line_ids
        # Create sheet and link to request
        self.expense_sheet_model.create(
            {
                "name": "Test Expense Sheet",
                "employee_id": self.expense_employee.id,
                "request_document_id": request_expense.id,
                "expense_line_ids": [Command.link(self.expense.id)],
            }
        )
        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_expense.expense_sheet_ids), 1)
        self.assertEqual(request_order.expense_sheet_counts, 1)

        # Delete request expense, sheet should delete too
        request_expense.unlink()

        request_order.invalidate_recordset()
        self.assertFalse(request_order.line_ids)
