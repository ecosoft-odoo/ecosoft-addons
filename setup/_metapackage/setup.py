import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-ecosoft-odoo-ecosoft-addons",
    description="Meta package for ecosoft-odoo-ecosoft-addons Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-account_financial_report_extension',
        'odoo14-addon-account_payment_tier_validation',
        'odoo14-addon-base_new_line_default',
        'odoo14-addon-base_report_extension',
        'odoo14-addon-dynamic_accounts_report',
        'odoo14-addon-fix_auth_ldap',
        'odoo14-addon-purchase_tax_adjust',
        'odoo14-addon-usability_account',
        'odoo14-addon-usability_account_spread_cost_revenue',
        'odoo14-addon-usability_auditlog',
        'odoo14-addon-usability_base_exception',
        'odoo14-addon-usability_hr_expense',
        'odoo14-addon-usability_l10n_th_account_tax_expense',
        'odoo14-addon-usability_l10n_th_account_tax_report',
        'odoo14-addon-usability_l10n_th_bank_payment_export',
        'odoo14-addon-usability_l10n_th_partner',
        'odoo14-addon-usability_product',
        'odoo14-addon-usability_purchase',
        'odoo14-addon-usability_purchase_guarantee',
        'odoo14-addon-usability_purchase_guarantee_activity',
        'odoo14-addon-usability_purchase_guarantee_operating_unit',
        'odoo14-addon-usability_purchase_request',
        'odoo14-addon-usability_purchase_work_acceptance',
        'odoo14-addon-usability_sale',
        'odoo14-addon-usability_webhooks',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
