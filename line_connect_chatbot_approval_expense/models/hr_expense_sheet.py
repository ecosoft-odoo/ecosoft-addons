# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from linebot.v3.messaging import Configuration

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def loop_attachment(self):
        # Get all attachment (Sheet + Expense)
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", "hr.expense.sheet"), ("res_id", "=", self.id)]
        )
        attachments += self.env["ir.attachment"].search(
            [
                ("res_model", "=", "hr.expense"),
                ("res_id", "in", self.expense_line_ids.ids),
            ]
        )
        # Generate all attachment with token
        attachments.generate_access_token()
        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")

        attach_vals = [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"File{idx + 1}: {attach.name}",
                        "flex": 3,
                        "size": "sm",
                        "gravity": "center",
                    },
                    {
                        "type": "button",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "Open",
                            "uri": f"{web_base_url}/web/image/{attach.id}"
                            f"?access_token={attach.access_token}",
                        },
                        "flex": 1,
                    },
                ],
            }
            for idx, attach in enumerate(attachments)
        ]

        # Convert the list of dictionaries to a JSON string with double quotes
        json_string = json.dumps(attach_vals, indent=2)

        # Need result without []
        result = json_string[1:-1]

        return result

    def loop_line_detail(self):
        content_line = [
            {
                "type": "box",
                "layout": "baseline",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{idx + 1}. {exp.name}",
                        "size": "sm",
                        "color": "#111111",
                        "wrap": True,
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": f"{exp.total_amount_company:,.2f} "
                        f"{exp.company_currency_id.symbol}",
                        "size": "sm",
                        "color": "#111111",
                        "margin": "md",
                        "align": "end",
                        "flex": 1,
                    },
                ],
            }
            for idx, exp in enumerate(self.expense_line_ids)
        ]
        # Convert the list of dictionaries to a JSON string with double quotes
        json_string = json.dumps(content_line, indent=2)

        # Need result without []
        result = json_string[1:-1]
        return result

    def _process_approved(self):
        return self.approve_expense_sheets()

    def _process_rejected(self, result):
        reason = result.get("reject_reason", False)
        return self.refuse_sheet(reason)

    def _create_quick_reply(self, event):
        postback_data = event.postback.data
        return [
            {
                "type": "text",
                "text": "Please select a reason for rejection:",
                "quickReply": {
                    "items": [
                        {
                            "type": "action",
                            "action": {
                                "type": "postback",
                                "label": "Incorrect Document",
                                "data": f"reject_reason=incorrect_document"
                                f"&{postback_data}",
                                "text": "Incorrect Document",
                            },
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "postback",
                                "label": "Insufficient",
                                "data": f"reject_reason=insufficient_info&"
                                f"{postback_data}",
                                "text": "Insufficient",
                            },
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "postback",
                                "label": "Not Authorized",
                                "data": f"reject_reason=not_authorized&{postback_data}",
                                "text": "Not Authorized",
                            },
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "postback",
                                "label": "Other Reason",
                                "data": f"reject_reason=other&{postback_data}",
                                "text": "Other Reason",
                            },
                        },
                    ]
                },
            }
        ]

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
                configuration,
                event.reply_token,
                "Your account was not found in the system. "
                "Please contact the administrator.",
            )
            return

        # Allow approve when state submit only

        if self.state != "submit":
            LineService.message_line_action(
                [
                    {
                        "type": "text",
                        "text": f"{self.number} is not state Submitted.",
                    }
                ],
                "push",
                user.partner_id.ids,
            )
            return

        action = result.get("action")
        self = self.with_user(user.id)
        if action == "approve":
            self._process_approved()
        if action == "reject":
            if not result.get("reject_reason", False):
                quick_reply_message = self._create_quick_reply(event)
                return LineService.message_line_action(
                    quick_reply_message,
                    "reply",
                    event.reply_token,
                )

            self._process_rejected(result)

        # Reply to manager
        LineService.message_line_action(
            [
                {
                    "type": "text",
                    "text": f"{self.number} has been successfully {action}.",
                }
            ],
            "reply",
            event.reply_token,
        )
