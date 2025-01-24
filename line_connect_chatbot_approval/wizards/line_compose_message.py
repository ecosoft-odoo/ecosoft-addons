# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class LINEComposer(models.TransientModel):
    _inherit = "line.compose.message"

    def _get_link_approval(self, code):
        base_url = self.env.context.get("base_url") or self.env.user.get_base_url()
        if not (self.model and self.res_id):
            raise UserError(_("This method requires both Model and Res ID to proceed."))
        original_record = self.env[self.model].browse(self.res_id)

        link_url = (
            f"{base_url}/line/webhook/approval"
            f"?model={original_record._name.replace('_', '.')}"
            f"&res_id={original_record.id}&code={code}"
            f"&access_token={self.partner_ids.line_access_token}"  # TODO: multi partner
        )
        return link_url
