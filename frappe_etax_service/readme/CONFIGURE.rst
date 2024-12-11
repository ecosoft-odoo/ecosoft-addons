Set up Frappe Server URL and Frappe Auth Token

#. Go to menu > Invoicing > Configurations > Settings
#. On title Ecosoft e-Tax Services set up Frappe Server URL and Frappe Auth Token

Note:
Frappe Server URL is the URL of the Frappe server where the e-Tax Service is installed. Frappe Auth Token is the token generated from the Frappe server.
Contract to the provider of the e-Tax Service for the Frappe Server URL and Frappe Auth Token.


Configurations Form template

#. Go to menu > Invoicing > Configurations > Etax Service > Doctype Code
#. Form name is name of odoo/frappe form, you need to use the same name as in odoo/frappe
#. Doctype code: This is the code with send to Frappe server which represent variant of tax invoice following:
    * 388: ใบกำกับภาษี
    * T02: ใบแจ้งหนี้/ใบกำกับภาษี
    * T03: ใบเสร็จรับเงิน/ใบกำกับภาษี
    * T04: ใบส่งของ/ใบกำกับภาษี
    * T05: ใบกำกับภาษีอย่างย่อ
    * T01: ใบรับ (ใบเสร็จรับเงิน)
    * 80: ใบเพิ่มหนี้
    * 81: ใบลดหนี้
