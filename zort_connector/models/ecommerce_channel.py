# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import _, fields, models


class ZortEcommerceChannel(models.Model):
    """
    Represents a Zort eCommerce channel configuration.

    Features:
    - Store channel settings (e.g., dummy customer, auto-create customer).
    - Example: Lazada
        name = "Lazada"
        code = "lazada"
        auto_create_customer = False

    Note:
        Sale channel, check from zort api on field `saleschannel`
        API: https://open-api.zortout.com/v4/Order/GetOrders
    """

    _name = "zort.ecommerce.channel"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Zort eCommerce Channel"
    _order = "sequence, name"
    _rec_name = "name"

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(
        required=True,
        tracking=True,
        help="Check from Zort API 'saleschannel'",
    )
    description = fields.Text()
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Platform Customer",
        help="Platform customer to use for this eCommerce channel",
    )
    auto_create_customer = fields.Boolean(
        help="Auto create customer for save customer data from this eCommerce channel",
        default=False,
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "The code of the eCommerce channel must be unique!",
        )
    ]

    def open_ecommerce_config_form(self):
        """Open eCommerce configuration form"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("E-commerce Channel"),
            "res_model": "zort.ecommerce.channel",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }
