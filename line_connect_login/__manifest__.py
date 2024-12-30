# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Line Connect - Login",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "summary": "Line Login",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "category": "Report",
    "depends": ["line_connect", "auth_oauth"],
    "data": [
        "data/auth_oauth_data.xml",
        "data/ir_config_parameter_data.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
