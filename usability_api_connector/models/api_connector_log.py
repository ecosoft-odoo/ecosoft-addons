# Copyright 2025 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ApiConnectorLog(models.Model):
    _name = "api.connector.log"
    _description = "Outbound API Call Log"
    _order = "create_date desc"

    api_code = fields.Char(required=True, index=True, readonly=True)
    api_name = fields.Char(readonly=True)
    end_point = fields.Char(readonly=True)
    res_model = fields.Char(index=True, readonly=True)
    res_id = fields.Many2oneReference(
        string="Record ID",
        model_field="res_model",
        index=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("success", "Success"),
            ("failed", "Failed"),
            ("draft", "Draft"),
        ],
        default="draft",
        required=True,
        index=True,
        readonly=True,
    )
    payload = fields.Text(readonly=True)
    result = fields.Text(readonly=True)
    error_message = fields.Text(readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Called By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    create_date = fields.Datetime(
        string="Called Date",
        readonly=True,
    )
