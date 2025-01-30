# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from linebot.v3.messaging import Configuration

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def loop_line_detail(self):
        content_line = [
            {
                "type": "box",
                "layout": "horizontal",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    # Product
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "xs",
                        "contents": [
                            {
                                "type": "text",
                                "text": exp.product_id.name,
                                "size": "xs",
                                "flex": 1,
                                "margin": "none",
                                "contents": [],
                            }
                        ],
                    },
                    # Description
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "xs",
                        "contents": [
                            {
                                "type": "text",
                                "text": exp.name,
                                "size": "xs",
                                "flex": 1,
                                "margin": "none",
                                "contents": [],
                            }
                        ],
                    },
                    # Price
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{exp.total_amount_company:,.2f} "
                                f"{exp.company_currency_id.symbol}",
                                "size": "sm",
                                "flex": 1,
                                "align": "end",
                            }
                        ],
                    },
                ],
            }
            for exp in self.expense_line_ids
        ]

        # Convert the list of dictionaries to a JSON string with double quotes
        json_string = json.dumps(content_line, indent=2)
        # Need result without []
        result = json_string[1:-1]
        return result

    def _process_approved(self):
        return self.approve_expense_sheets()

    def _process_rejected(self):
        # TODO: How can we add reason in LINE?
        self.refuse_sheet("Rejected")
        return self.refuse_sheet("Rejected")

    def _process_approval(self, event, result):
        channel_access_token = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("line.channel_access_token")
        )
        configuration = Configuration(access_token=channel_access_token)
        user = self.env["res.users"].search(
            [("line_access_token", "=", event.source.user_id)]
        )
        LineService = self.env["line.service"]

        if not user:
            # If not user in system, we use reply to manager.
            # because partner not found.
            LineService.message_line_reply(
                "Your account was not found in the system. "
                "Please contact the administrator.",
                configuration,
                event.reply_token,
            )
            return

        # Allow approve when state submit only

        if self.state != "submit":
            LineService.message_line_push(
                [
                    {
                        "type": "text",
                        "text": f"{self.number} is not state Submitted.",
                    }
                ],
                user.partner_id.ids,
            )
            return

        action = result.get("action")
        self = self.with_user(user.id)
        if action == "approve":
            self._process_approved()
        if action == "reject":
            self._process_rejected()

        # Reply to manager
        LineService.message_line_push(
            [
                {
                    "type": "text",
                    "text": f"{self.number} has been successfully {action}.",
                }
            ],
            user.partner_id.ids,
        )
