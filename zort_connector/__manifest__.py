# -*- coding: utf-8 -*-
{
    'name': "zort_connector",
    'summary': "Connects Odoo with Zort",
    'description': """
Long description of module's purpose
    """,
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'author': "Ecosoft., Ltd.",
    'maintainers': ['theerayuta@ecosoft.co.th'],
    'website': "https://www.yourcompany.com",
    'depends': ['sale_management'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/partner_data.xml',
        'data/product_data.xml',
        'views/res_config_settings_view.xml',
        'views/sale_order_view.xml',
        'views/product_template_view.xml',
    ],
}

