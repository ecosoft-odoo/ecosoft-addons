# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class LINETemplate(models.Model):
    _name = "line.template"
    _description = "LINE Templates"

    name = fields.Char(
        required=True,
    )
    template_json = fields.Text()
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
    )
