# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Line Connect - Chat Bot",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "summary": "",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "category": "Report",
    "depends": ["web", "mail", "line_connect", "account"],  # TODO: For test only
    "data": [
        "security/ir.model.access.csv",
        "security/line_chat_security_groups.xml",
        "data/ir_config_parameter_data.xml",
        "data/ir_cron.xml",
        "data/line_template_data.xml",
        "views/res_config_settings_views.xml",
        "views/line_template_views.xml",
        "views/res_partner_views.xml",
        "views/mail_channel_views.xml",
        "views/line_message_views.xml",
        "views/line_message_broadcast_views.xml",
        "wizards/line_compose_message_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "line_connect_chatbot/static/src/models/*/*.js",
        ],
        "web.assets_qweb": [
            "line_connect_chatbot/static/src/components/*/*.xml",
        ],
    },
    "external_dependencies": {
        "python": ["line-bot-sdk"],  # TODO: May be not needed
    },
    "installable": True,
    "maintainers": ["Saran440"],
}
