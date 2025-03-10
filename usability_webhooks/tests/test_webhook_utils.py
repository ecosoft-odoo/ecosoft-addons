from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWebhookUtils(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Initialize test data
        cls.webhook_utils = cls.env["webhook.utils"]
        cls.partner_model = "res.partner"

        # Create test partner
        cls.test_partner = cls.env.ref("base.res_partner_3")
        cls.test_partner.write(
            {
                "name": "Test Partner",
                "email": "test@example.com",
            }
        )

    def test_01_create_data(self):
        """Test creating a new partner via webhook"""
        vals = {
            "payload": {
                "name": "New Partner",
                "email": "new@example.com",
            }
        }
        result = self.webhook_utils.create_data(self.partner_model, vals)
        self.assertTrue(result["is_success"])
        self.assertTrue(result["result"]["id"])

        # Verify created partner
        partner = self.env[self.partner_model].browse(result["result"]["id"])
        self.assertEqual(partner.name, "New Partner")
        self.assertEqual(partner.email, "new@example.com")

    def test_02_update_data(self):
        """Test updating existing partner via webhook"""
        vals = {
            "search_key": {
                "id": self.test_partner.id,
            },
            "payload": {
                "name": "Updated Partner",
                "email": "updated@example.com",
            },
        }
        result = self.webhook_utils.update_data(self.partner_model, vals)
        self.assertTrue(result["is_success"])

        # Verify updated partner
        self.assertEqual(self.test_partner.name, "Updated Partner")
        self.assertEqual(self.test_partner.email, "updated@example.com")

    def test_03_search_data(self):
        """Test searching partners via webhook"""
        vals = {
            "payload": {
                "search_field": ["name", "email"],
                "search_domain": "[('name', '=', 'Test Partner')]",
                "limit": 1,
            }
        }
        result = self.webhook_utils.search_data(self.partner_model, vals)
        self.assertTrue(result["is_success"])
        self.assertTrue(result["result"])
        self.assertEqual(result["result"][0]["name"], "Test Partner")

    def test_04_create_with_many2one(self):
        """Test creating record with many2one relation"""
        vals = {
            "payload": {
                "name": "New Company",
                "country_id": "Thailand",  # Using name instead of ID
            },
            "auto_create": {"country_id": {"name": "Thailand"}},
        }
        result = self.webhook_utils.create_data("res.company", vals)
        self.assertTrue(result["is_success"])

    def test_05_create_with_attachment(self):
        """Test creating record with attachment"""
        vals = {
            "payload": {
                "name": "With Attachment",
                "attachment_ids": [
                    {
                        "name": "test.txt",
                        "datas": "SGVsbG8gV29ybGQ=",  # Base64 encoded "Hello World"
                    }
                ],
            }
        }
        result = self.webhook_utils.create_data(self.partner_model, vals)
        self.assertTrue(result["is_success"])

        # Verify attachment
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self.partner_model),
                ("res_id", "=", result["result"]["id"]),
            ]
        )
        self.assertTrue(attachment)
        self.assertEqual(attachment.name, "test.txt")

    def test_06_call_function(self):
        """Test calling model function via webhook"""
        vals = {
            "search_key": {
                "id": self.test_partner.id,
            },
            "payload": {
                "method": "_compute_display_name",
                "parameter": {},
            },
        }
        result = self.webhook_utils.call_function(self.partner_model, vals)
        self.assertTrue(result["is_success"])

    def test_07_invalid_search_key(self):
        """Test error handling for invalid search key"""
        vals = {
            "payload": {
                "name": "Test",
            }
        }
        with self.assertRaises(ValidationError):
            self.webhook_utils.update_data(self.partner_model, vals)
