# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestUsabilityWebhooks(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_data(self):
        self.env["webhook.utils"].create_data(
            model="res.users",
            vals={
                "payload": {
                    "name": "New API",
                    "login": "new_api",
                }
            },
        )
