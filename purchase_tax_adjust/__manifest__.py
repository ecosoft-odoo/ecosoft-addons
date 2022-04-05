# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Purchase Order minor tax adjustment",
    "version": "14.0.1.0.0",
    "summary": """
Allow minor adjustment in purchase order line (optional=hide),
which reflect in total tax amount
    """,
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "category": "Purchase",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "license": "AGPL-3",
    "depends": ["purchase"],
    "data": [
        "views/purchase_view.xml",
    ],
    "auto_install": False,
    "installable": True,
    "maintainers": ["kittiu"],
}
