# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    @api.onchange("config_ktb_company_id")
    def onchange_config_ktb_company_id(self):
        config_ktb_company = self.config_ktb_company_id
        if config_ktb_company and config_ktb_company.depend_id:
            self[
                config_ktb_company.depend_id.field_id.name
            ] = config_ktb_company.depend_id

    @api.onchange("config_ktb_sender_name")
    def onchange_config_ktb_sender_name(self):
        config_ktb_sender = self.config_ktb_sender_name
        if config_ktb_sender and config_ktb_sender.depend_id:
            self[
                config_ktb_sender.depend_id.field_id.name
            ] = config_ktb_sender.depend_id
