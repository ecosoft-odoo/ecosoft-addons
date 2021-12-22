This module base off `base_exception` and add exception messages on following cases,

1. PR -> PO :: Purchase Order total amount shouldn't exceed that of PR amount.
2. PO -> Bill :: Vendor Bills(s) total amount shouldn't exceed that of PO amount.

When the exception occur, user can by pass it by set flag "Bypass Amount Exception",
then click confirm again.
