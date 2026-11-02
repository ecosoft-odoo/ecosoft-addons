import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-ecosoft-odoo-ecosoft-addons",
    description="Meta package for ecosoft-odoo-ecosoft-addons Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-usability_webhooks>=16.0dev,<16.1dev',
        'odoo-addon-usability_webhooks_queue_job>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
