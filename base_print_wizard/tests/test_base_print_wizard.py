# Copyright 2026 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestBasePrintWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.person, cls.company = cls.env["res.partner"].search([], limit=2)
        cls.person.company_type = "person"
        cls.company.company_type = "company"
        cls.report_all = cls._create_report("All Partners")
        cls.report_person = cls._create_report(
            "Persons Only", "[('company_type', '=', 'person')]"
        )

    @classmethod
    def _create_report(cls, name, domain_form=False, **values):
        return cls.env["ir.actions.report"].create(
            {
                "name": name,
                "model": "res.partner",
                "report_type": "qweb-html",
                "report_name": "base_print_wizard.test_report",
                "show_in_wizard": True,
                "domain_form": domain_form,
                **values,
            }
        )

    def _wizard_model(self, records):
        return self.env["base.print.wizard"].with_context(
            active_model=records._name,
            active_ids=records.ids,
        )

    def test_domain_must_match_all_selected_records(self):
        report_ids = self._wizard_model(self.person)._get_available_report_ids()
        self.assertIn(self.report_all.id, report_ids)
        self.assertIn(self.report_person.id, report_ids)

        records = self.person | self.company
        report_ids = self._wizard_model(records)._get_available_report_ids()
        self.assertIn(self.report_all.id, report_ids)
        self.assertNotIn(self.report_person.id, report_ids)

    def test_report_groups_are_respected(self):
        restricted_group = self.env["res.groups"].create(
            {"name": "Restricted Print Report"}
        )
        restricted_report = self._create_report(
            "Restricted Report",
            groups_id=[Command.set(restricted_group.ids)],
        )

        report_ids = self._wizard_model(self.person)._get_available_report_ids()
        self.assertNotIn(restricted_report.id, report_ids)

    def test_selected_report_is_validated_server_side(self):
        hidden_report = self._create_report("Hidden Report", show_in_wizard=False)
        wizard = self._wizard_model(self.person).create({"doctype": hidden_report.id})

        with self.assertRaises(UserError):
            wizard._validate_report()

    def test_report_model_must_match_active_model(self):
        wizard = (
            self.env["base.print.wizard"]
            .with_context(
                active_model="res.users",
                active_ids=self.env.user.ids,
            )
            .create({"doctype": self.report_all.id})
        )

        with self.assertRaises(UserError):
            wizard._validate_report()

    def test_invalid_domain_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_report("Invalid Domain", "not a domain")
