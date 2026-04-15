# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Zort Connector Queue",
    "summary": "Process Zort sync logs via Queue Jobs",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["zort_connector", "queue_job_cron"],
    "data": [
        "data/ir_cron_data.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["Saran440"],
}
