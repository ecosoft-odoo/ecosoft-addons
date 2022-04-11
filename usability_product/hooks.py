# Copyright 2018 Brainbean Apps
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Product Advance, Expense and 3 type procurement are not editable
    product_not_edit = (
        env.ref("hr_expense_advance_clearing.product_emp_advance")
        + env.ref("l10n_th_gov_purchase_request.product_type_001")
        + env.ref("l10n_th_gov_purchase_request.product_type_002")
        + env.ref("l10n_th_gov_purchase_request.product_type_003")
        + env.ref("hr_expense.product_product_fixed_cost")
        + env.ref("budget_activity_purchase_deposit.product_purchase_deposit")
    )
    product_not_edit.write({"product_important": "not_edit"})
