# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json

from odoo import fields, models


class APILog(models.Model):
    _name = "api.log"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "API Logs"
    _rec_name = "id"
    _order = "id desc"

    data = fields.Text(tracking=True)
    model = fields.Char(tracking=True)
    route = fields.Char(tracking=True)
    result = fields.Text(tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="draft",
        tracking=True,
    )

    def action_call_api(self):
        try:
            res = self.env["webhook.utils"].create_data(
                self.model, json.loads(self.data)
            )
            state = "done" if res["is_success"] else "failed"
            self.write({"result": res, "state": state})
        except Exception as e:
            res = {
                "is_success": False,
                "messages": e,
            }
            self.write({"result": res, "state": "failed"})
        return True
