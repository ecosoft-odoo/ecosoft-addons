# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.orm.model_classes import add_to_registry
from odoo.tests.common import TransactionCase

TEST_MODELS = ("webhook.test.record", "webhook.test.line")


class WebhookTestCommon(TransactionCase):
    """Register test models using ``webhook.outbound.mixin`` for the class"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_test_models()
        cls.Record = cls.env["webhook.test.record"]
        cls.Tag = cls.env["res.partner.category"]
        cls.tag_a, cls.tag_b = cls.Tag.create(
            [{"name": "Webhook Tag A"}, {"name": "Webhook Tag B"}]
        )
        cls.record = cls.Record.create({"name": "Common Test"})

    @classmethod
    def _setup_test_models(cls):
        from .webhook_test_models import WebhookTestLine, WebhookTestRecord

        for model_class in (WebhookTestRecord, WebhookTestLine):
            add_to_registry(cls.registry, model_class)
            cls.addClassCleanup(cls.registry.__delitem__, model_class._name)
        cls.registry._setup_models__(cls.env.cr, TEST_MODELS)
        cls.registry.init_models(cls.env.cr, TEST_MODELS, {"models_to_check": True})
        cls.env["ir.access"].create(
            [
                {
                    "name": f"{model_name} user",
                    "model_id": cls.env["ir.model"]._get_id(model_name),
                    "group_id": cls.env.ref("base.group_user").id,
                    "operation": "crud",
                }
                for model_name in TEST_MODELS
            ]
        )
