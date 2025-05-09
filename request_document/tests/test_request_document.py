# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo_test_helper import FakeModelLoader

from odoo import Command
from odoo.tests.common import TransactionCase


class TestRequestDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()

        from .request_document_tester import RequestDocument

        cls.loader.update_registry((RequestDocument,))

        cls.request_obj = cls.env["request.order"]

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_01_check_sequence_request(self):
        # Create request with default
        request = self.request_obj.create({})
        self.assertNotEqual(request.name, "/")
        self.assertRegex(request.name, r"^RQ\d+")

        # Create request with name = "/", it should same as not send name
        request = self.request_obj.create({"name": "/"})
        self.assertNotEqual(request.name, "/")
        self.assertRegex(request.name, r"^RQ\d+")

        # Create request with name = "Test - Name"
        request = self.request_obj.create({"name": "Test - Name"})
        self.assertNotEqual(request.name, "/")
        self.assertEqual(request.name, "Test - Name")

    def test_02_process_request(self):
        request = self.request_obj.create(
            {"line_ids": [Command.create({"request_type": "tester"})]}
        )
        self.assertEqual(len(request.line_ids), 1)
        # name should RQXXXXXX - X
        self.assertRegex(request.line_ids.name, r"^RQ\d+")
        self.assertEqual(request.line_ids.currency_id, request.company_id.currency_id)
        self.assertEqual(request.state, "draft")
        request.action_submit()
        self.assertEqual(request.state, "submit")
        request.action_approve()
        self.assertEqual(request.state, "approve")
        request.action_process_document()
        self.assertEqual(request.state, "done")
        request.action_cancel()
        self.assertEqual(request.state, "cancel")
        request.action_draft()
        self.assertEqual(request.state, "draft")
