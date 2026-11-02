import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-ecosoft-odoo-ecosoft-addons",
    description="Meta package for ecosoft-odoo-ecosoft-addons Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-usability_webhooks',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 13.0',
    ]
)
