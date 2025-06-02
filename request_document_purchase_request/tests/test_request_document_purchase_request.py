# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestRequestDocumentPurchaseRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchase_request_obj = cls.env["purchase.request"]
        cls.purchase_request_line_obj = cls.env["purchase.request.line"]
        cls.picking_type_id = cls.env.ref("stock.picking_type_in")
        vals = {
            "group_id": cls.env["procurement.group"].create({}).id,
            "picking_type_id": cls.picking_type_id.id,
            "requested_by": SUPERUSER_ID,
        }
        cls.purchase_request = cls.purchase_request_obj.create(vals)
        vals = {
            "name": "Test line",
            "request_id": cls.purchase_request.id,
            "product_id": cls.env.ref("product.product_product_13").id,
            "product_uom_id": cls.env.ref("uom.product_uom_unit").id,
            "product_qty": 5.0,
        }
        cls.purchase_request_line_obj.create(vals)

        cls.request_model = cls.env["request.order"]

    def test_01_process_request_purchase_request(self):
        # Create request order and line
        request_order = self.request_model.create(
            {"line_ids": [Command.create({"request_type": "purchase_request"})]}
        )
        request_purchase_request = request_order.line_ids
        # Link to request
        self.purchase_request.request_document_id = request_purchase_request.id
        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_purchase_request.purchase_request_ids), 1)
        self.assertEqual(request_order.purchase_request_counts, 1)

        # Check edit expense related request. it shouldn't editable
        error_msg = (
            "You cannot modify this record because the related "
            "Request Document is not in 'Done' state."
        )
        with self.assertRaisesRegex(UserError, error_msg):
            self.purchase_request.name = "NEW TEST PR"

        # Allow edit if send context `allow_edit`
        self.purchase_request.with_context(allow_edit=1).name = "NEW TEST PR"

        self.assertEqual(
            request_purchase_request.name_document, self.purchase_request.name
        )
        # Open details, it should open purchase request
        action = request_purchase_request.open_request_document()
        self.assertEqual(action["res_model"], "purchase.request")
        self.assertEqual(action["res_id"], self.purchase_request.id)

        # Config company to auto approve
        request_order.company_id.request_document_pr_state = "approved"
        request_order.action_submit()
        self.assertEqual(request_order.state, "submit")
        request_order.action_approve()
        self.assertEqual(request_order.state, "approve")
        self.assertEqual(self.purchase_request.state, "draft")
        request_order.action_process_document()
        self.assertEqual(request_order.state, "done")
        self.assertEqual(self.purchase_request.state, "approved")

        # Check change value purchase request after request done. it should do it.
        self.purchase_request.name = "TEST CHANGE NAME AFTER REQUEST DONE"

        # Check open purchase request from smart button
        action = request_order.action_open_purchase_request()
        self.assertEqual(action["res_model"], "purchase.request")
        self.assertEqual(action["domain"][0][2], [self.purchase_request.id])

    def test_02_delete_request_purchase_request(self):
        # Create request order and line
        request_order = self.request_model.create(
            {"line_ids": [Command.create({"request_type": "purchase_request"})]}
        )
        request_purchase_request = request_order.line_ids
        # Link to request
        self.purchase_request.request_document_id = request_purchase_request.id
        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_purchase_request.purchase_request_ids), 1)
        self.assertEqual(request_order.purchase_request_counts, 1)

        # Delete request purchase request, pr should delete too
        request_purchase_request.unlink()

        request_order.invalidate_recordset()
        self.assertFalse(request_order.line_ids)
