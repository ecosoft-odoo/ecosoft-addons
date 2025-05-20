# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.request_document.tests.test_request_document import TestRequestDocument


@tagged("-at_install", "post_install")
class TestRequestDocumentTierValidation(TestRequestDocument):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tier_def_obj = cls.env["tier.definition"]

        # Create users
        group_ids = (
            cls.env.ref("base.group_system")
            + cls.env.ref("account.group_account_manager")
        ).ids
        cls.test_user_1 = cls.env["res.users"].create(
            {
                "name": "John",
                "login": "test1",
                "groups_id": [(6, 0, group_ids)],
                "email": "test@examlple.com",
            }
        )

        # Create tier validation
        cls.tier_def_obj.create(
            {
                "model_id": cls.env.ref("request_document.model_request_order").id,
                "review_type": "individual",
                "reviewer_id": cls.test_user_1.id,
            }
        )

    def test_01_get_tier_validation_model_names(self):
        self.assertIn(
            "request.order", self.tier_def_obj._get_tier_validation_model_names()
        )

    def test_02_request_validation(self):
        request = self.request_obj.create({})
        request.action_submit()
        reviews = request.request_validation()
        self.assertTrue(reviews)
        record = request.with_user(self.test_user_1.id)
        self.assertFalse(record.validated)
        record.invalidate_model()
        record.validate_tier()
        self.assertTrue(record.validated)
