# Copyright 2017-19 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def restart_validation(self):
        """restart tier with clear data work acceptance committee"""
        if self._name == "work.acceptance":
            for rec in self:
                rec.work_acceptance_committee_ids.write(
                    {
                        "status": "",
                        "note": "",
                    }
                )
        return super().restart_validation()
