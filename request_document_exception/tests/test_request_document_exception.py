# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.request_document.tests.test_request_document import TestRequestDocument


@tagged("-at_install", "post_install")
class TestRequestDocumentException(TestRequestDocument):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.exception_no_line = cls.env.ref(
            "request_document_exception.request_excep_no_line"
        )
        cls.request_model = cls.env["request.order"]

    def test_01_request_document_exception(self):
        self.exception_no_line.active = True
        request_order = self.request_model.create({})

        self.assertEqual(request_order.state, "draft")
        self.assertFalse(request_order.main_exception_id)

        request_order.action_submit()
        self.assertEqual(request_order.state, "draft")
        self.assertTrue(request_order.main_exception_id)

        request_except_confirm = (
            self.env["request.exception.confirm"]
            .with_context(
                active_id=request_order.id,
                active_ids=[request_order.id],
                active_model=request_order._name,
            )
            .create({"ignore": True})
        )
        request_except_confirm.action_confirm()

        self.assertEqual(request_order.state, "submit")

    def test_02_request_document_no_exception(self):
        request_order = self.request_model.create({})

        self.assertEqual(request_order.state, "draft")
        request_order.action_submit()
        self.assertEqual(request_order.state, "submit")
