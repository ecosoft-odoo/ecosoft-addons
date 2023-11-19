def prepare_data(doc):
    if doc._name == "account.move":  # Invoice
        return prepare_data_invoice(doc)
    if doc._name == "account.payment":
        return prepare_data_payment(doc)


def prepare_data_invoice(doc):
    d = {}
    d["currency_code"] = doc.currency_id.name
    d["document_type_code"] = doc.etax_doctype
    d["document_id"] = doc.name
    d["document_issue_dtm"] = doc.invoice_date and doc.invoice_date.strftime("%Y-%m-%dT%H:%M:%S")
    d["create_purpose_code"] = doc.create_purpose_code
    d["create_purpose"] = doc.create_purpose
    d["ref_document_id"] = doc.debit_origin_id.name or doc.reversed_entry_id.name or doc.replaced_entry_id.name
    d["ref_document_issue_dtm"] = doc._get_origin_inv_date()
    d["ref_document_type_code"] = (
        doc.debit_origin_id.etax_doctype
        or doc.reversed_entry_id.etax_doctype
        or doc.replaced_entry_id.etax_doctype
    )
    d["buyer_ref_document"] = doc.payment_reference
    d["seller_branch_id"] = doc._get_branch_id() or doc.company_id.branch
    d["source_system"] = doc.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    d["send_mail"] = (
        "Y"
        if doc.env["ir.config_parameter"]
        .sudo()
        .get_param("frappe_etax_service.is_send_etax_email")
        else "N"
    )
    d["seller_tax_id"] = doc.company_id.vat
    d["buyer_name"] = doc.partner_id.name
    d["buyer_type"] = "TXID"  # TXID, NIDN, CCPT, OTHR (no taxid)
    d["buyer_tax_id"] = doc.partner_id.vat
    d["buyer_branch_id"] = doc.partner_id.branch or "00000"
    d["buyer_email"] = doc.partner_id.email
    d["buyer_zip"] = doc.partner_id.zip
    d["buyer_building_name"] = ""
    d["buyer_building_no"]  = ""
    d["buyer_address_line1"] = doc.partner_id.street
    d["buyer_address_line2"] = doc.partner_id.street2
    d["buyer_address_line3"] = ""
    d["buyer_address_line4"] = ""
    d["buyer_address_line5"] = ""
    d["buyer_city_name"] = doc.partner_id.city
    d["buyer_country_code"] = doc.partner_id.country_id and doc.partner_id.country_id.code or ""
    doc_lines = []
    for line in doc.invoice_line_ids.filtered(lambda l: not l.display_type and l.price_unit > 0):
        doc_lines.append(
            {
                "product_code": line.product_id and line.product_id.default_code,
                "product_name": line.product_id and line.product_id.name or line.name,
                "product_price": line.price_unit,
                "product_quantity": line.quantity,
                "line_tax_type_code": line.tax_ids.name and "VAT" or "FRE",
                "line_tax_rate": line.tax_ids and line.tax_ids[0].amount or 0.00,
                "line_base_amount": line.tax_ids and line.price_subtotal or 0.00,
                "line_tax_amount": line.tax_ids and (line.price_total - line.price_subtotal) or 0.0,
                "line_total_amount": line.price_total,
            }
        )
    d["line_item_information"] = doc_lines
    d["original_amount_untaxed"] = doc._get_additional_amount()[0]
    d["final_amount_untaxed"] = doc._get_additional_amount()[2]
    d["adjust_amount_untaxed"] = doc._get_additional_amount()[2]
    return d


def prepare_data_payment(doc):
    d = {}
    d["currency_code"] = doc.currency_id.name
    d["document_type_code"] = doc.etax_doctype
    d["document_id"] = doc.name
    d["document_issue_dtm"] = doc.date and doc.date.strftime("%Y-%m-%dT%H:%M:%S")
    # As of now, no use for payment
    d["create_purpose_code"] =  ""
    d["create_purpose"] =  ""
    d["ref_document_id"] =  ""
    d["ref_document_issue_dtm"] =  ""
    d["ref_document_type_code"] = ""
    # --
    d["buyer_ref_document"] = doc.ref
    d["seller_branch_id"] = doc._get_branch_id() or doc.company_id.branch
    d["source_system"] = doc.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    d["send_mail"] = (
        "Y"
        if doc.env["ir.config_parameter"]
        .sudo()
        .get_param("frappe_etax_service.is_send_etax_email")
        else "N"
    )
    d["seller_tax_id"] = doc.company_id.vat
    d["buyer_name"] = doc.partner_id.name
    d["buyer_type"] = "TXID"  # TXID, NIDN, CCPT, OTHR (no taxid)
    d["buyer_tax_id"] = doc.partner_id.vat
    d["buyer_branch_id"] = doc.partner_id.branch or "00000"
    d["buyer_email"] = doc.partner_id.email
    d["buyer_zip"] = doc.partner_id.zip
    d["buyer_building_name"] = ""
    d["buyer_building_no"]  = ""
    d["buyer_address_line1"] = doc.partner_id.street
    d["buyer_address_line2"] = doc.partner_id.street2
    d["buyer_address_line3"] = ""
    d["buyer_address_line4"] = ""
    d["buyer_address_line5"] = ""
    d["buyer_city_name"] = doc.partner_id.city
    d["buyer_country_code"] = doc.partner_id.country_id and doc.partner_id.country_id.code or ""
    doc_lines = []
    for line in doc.tax_invoice_ids:
        doc_lines.append(
            {
                "product_code": line.tax_invoice_number,
                "product_name": line.tax_invoice_number,
                "product_price": line.tax_base_amount,
                "product_quantity": 1,
                "line_tax_type_code": line.tax_line_id.name and "VAT" or "FRE",
                "line_tax_rate": line.tax_line_id.amount,
                "line_base_amount": line.tax_base_amount,
                "line_tax_amount": line.balance,
                "line_total_amount": line.tax_base_amount + line.balance,
            }
        )
    d["line_item_information"] = doc_lines
    # As of now, no use for payment
    d["original_amount_untaxed"] = False
    d["final_amount_untaxed"] = False
    d["adjust_amount_untaxed"] = False
    # --
    return d
