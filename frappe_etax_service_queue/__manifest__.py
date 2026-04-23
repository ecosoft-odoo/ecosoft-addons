# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Connector to Frappe eTax service (Queue)",
    "summary": "Add queue job to frappe eTax service",
    "version": "18.0.1.0.0",
    "author": "Ecosoft",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "frappe_etax_service",
        "queue_job",
    ],
    "data": [
        "wizards/etax_doctype_wizard.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
