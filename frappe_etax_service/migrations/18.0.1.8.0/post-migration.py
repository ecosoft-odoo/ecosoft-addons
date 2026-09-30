# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Include archived contacts and preserve explicitly configured recipients.
    cr.execute(
        """
        UPDATE res_partner
           SET email_etax = email
         WHERE (email_etax IS NULL OR BTRIM(email_etax) = '')
           AND email IS NOT NULL
           AND BTRIM(email) != ''
        """
    )
    _logger.info("Copied existing email to e-Tax Email for %s partners", cr.rowcount)
    # Existing companies keep optional email delivery on upgrade.
    cr.execute(
        """
        UPDATE res_company
           SET require_etax_email = FALSE
         WHERE require_etax_email IS NULL
        """
    )
