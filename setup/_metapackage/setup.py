import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-ecosoft-odoo-ecosoft-addons",
    description="Meta package for ecosoft-odoo-ecosoft-addons Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_asset_disable_create>=15.0dev,<15.1dev',
        'odoo-addon-account_asset_product>=15.0dev,<15.1dev',
        'odoo-addon-account_financial_report_extension>=15.0dev,<15.1dev',
        'odoo-addon-account_move_reconcile_no_cancel>=15.0dev,<15.1dev',
        'odoo-addon-account_reconciliation_widget_extension>=15.0dev,<15.1dev',
        'odoo-addon-base_hide_delete_view>=15.0dev,<15.1dev',
        'odoo-addon-base_new_line_default>=15.0dev,<15.1dev',
        'odoo-addon-base_report_extension>=15.0dev,<15.1dev',
        'odoo-addon-ecosoft_services>=15.0dev,<15.1dev',
        'odoo-addon-frappe_etax_service>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_cash_basis>=15.0dev,<15.1dev',
        'odoo-addon-l10n_th_account_wht_cert_form_sequence>=15.0dev,<15.1dev',
        'odoo-addon-l10n_th_hr_expense_cash_basis>=15.0dev,<15.1dev',
        'odoo-addon-mrp_price_difference>=15.0dev,<15.1dev',
        'odoo-addon-mrp_stock_analytic>=15.0dev,<15.1dev',
        'odoo-addon-product_readonly>=15.0dev,<15.1dev',
        'odoo-addon-request_document>=15.0dev,<15.1dev',
        'odoo-addon-request_document_exception>=15.0dev,<15.1dev',
        'odoo-addon-request_document_expense>=15.0dev,<15.1dev',
        'odoo-addon-request_document_purchase_request>=15.0dev,<15.1dev',
        'odoo-addon-request_document_tier_validation>=15.0dev,<15.1dev',
        'odoo-addon-stock_account_visible_valuation>=15.0dev,<15.1dev',
        'odoo-addon-usability_webhooks>=15.0dev,<15.1dev',
        'odoo-addon-usability_webhooks_queue_job>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
