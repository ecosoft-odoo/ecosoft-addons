# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ZortSyncLog(models.Model):
    _name = "zort.sync.log"
    _description = "Zort Sync Log"
    _order = "sync_from desc, page desc"
    _rec_name = "id"
    _rec_names_search = ["id"]

    sync_from = fields.Datetime(readonly=True)
    sync_to = fields.Datetime(readonly=True)
    page = fields.Integer(default=1, readonly=True)
    total_pages = fields.Integer(default=0, readonly=True)
    state = fields.Selection(
        selection=[
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="in_progress",
        readonly=True,
    )
    order_created = fields.Integer(string="Created", readonly=True, default=0)
    order_updated = fields.Integer(string="Updated", readonly=True, default=0)
    order_failed = fields.Integer(string="Failed", readonly=True, default=0)
    error_message = fields.Text(readonly=True)
