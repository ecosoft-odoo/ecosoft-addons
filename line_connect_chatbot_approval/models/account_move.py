# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def handle_approval_document(self, **kwargs):
        code = kwargs["code"]
        partner = (
            self.env["res.partner"]
            .sudo()
            .search([("line_access_token", "=", kwargs["access_token"])])
        )
        document = self.env[kwargs["model"]].browse(int(kwargs["res_id"]))

        # Add permission document
        if partner.user_ids:
            document = document.with_user(partner.user_ids.id)
            message = False
        else:
            document = document.sudo()
            partner_approval = {
                "approve": f"Approved by {partner.name}",
                "reject": f"Rejected by {partner.name}",
            }
            message = partner_approval[code]

        # Action to do
        if code == "approve":
            document.action_post()
        if code == "reject":
            document.button_cancel()

        # Log message for partner approved/rejected
        if message:
            user_bot = self.env.ref("base.user_root")
            document.with_user(user_bot).message_post(body=message)
        return
