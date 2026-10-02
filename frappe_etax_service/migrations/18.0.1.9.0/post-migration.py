# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE account_payment
           SET enable_etax = FALSE
         WHERE enable_etax
           AND (partner_type != 'customer' OR payment_type != 'inbound')
        """
    )
    _logger.info("Disabled e-Tax button for %s non-customer payments", cr.rowcount)
