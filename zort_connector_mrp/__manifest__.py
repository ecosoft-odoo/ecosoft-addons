# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Zort Connector - MRP",
    "summary": "Process Zort with BoM Kit",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["zort_connector", "mrp"],
    "data": [
        "data/api_config_data.xml",
        "data/ir_cron_data.xml",
        "views/mrp_bom_views.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["Saran440"],
}
