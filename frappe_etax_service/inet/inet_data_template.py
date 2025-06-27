def prepare_data(doc):
    if doc._name == "account.move":  # Invoice
        return prepare_data_invoice(doc)
    if doc._name == "account.payment":
        return prepare_data_payment(doc)


def prepare_data_invoice(doc):
    config_params = doc.env["ir.config_parameter"].sudo()

    # prepare invoice lines
    invoice_lines_etax = doc.invoice_line_ids.filtered(
        lambda inv_line: not inv_line.display_type
        and inv_line.price_unit > 0
        and not inv_line.not_send_to_etax
    )
    doc_lines = [
        {
            "product_code": line.product_id and line.product_id.default_code or "",
            "product_name": line.product_id and line.product_id.name or line.name,
            "product_price": line.price_unit,
            "product_quantity": line.quantity,
            "line_tax_type_code": line.tax_ids.name and "VAT" or "FRE",
            "line_tax_rate": line.tax_ids and line.tax_ids[0].amount or 0.00,
            "line_base_amount": line.tax_ids and line.price_subtotal or 0.00,
            "line_tax_amount": line.tax_ids
            and (line.price_total - line.price_subtotal)
            or 0.0,
            "line_total_amount": line.price_total,
        }
        for line in invoice_lines_etax
    ]

    d = {
        "currency_code": doc.currency_id.name,
        "document_type_code": doc.etax_doctype,
        "document_id": doc.name,
        "document_issue_dtm": doc.invoice_date
        and doc.invoice_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "create_purpose_code": doc.create_purpose_code,
        "create_purpose": doc.create_purpose,
        "ref_document_id": doc._get_ref_document_id(),
        "ref_document_issue_dtm": doc._get_origin_inv_date(),
        "ref_document_type_code": doc._get_ref_document_type_code(),
        "buyer_ref_document": doc.payment_reference,
        "seller_branch_id": doc._get_branch_id() or doc.company_id.branch,
        "source_system": config_params.get_param("web.base.url", ""),
        "send_mail": "Y"
        if config_params.get_param("frappe_etax_service.is_send_etax_email")
        else "N",
        "seller_tax_id": doc.company_id.vat,
        "buyer_name": doc.partner_id.name,
        "buyer_type": "TXID",  # TXID, NIDN, CCPT, OTHR (no taxid)
        "buyer_tax_id": doc.partner_id.vat,
        "buyer_branch_id": doc.partner_id.branch or "00000",
        "buyer_email": doc.partner_id.email,
        "buyer_zip": doc.partner_id.zip,
        "buyer_building_name": "",
        "buyer_building_no": "",
        "buyer_address_line1": doc.partner_id.street,
        "buyer_address_line2": doc.partner_id.street2,
        "buyer_address_line3": "",
        "buyer_address_line4": "",
        "buyer_address_line5": "",
        "buyer_city_name": doc.partner_id.city,
        "buyer_country_code": doc.partner_id.country_id
        and doc.partner_id.country_id.code
        or "",
        "line_item_information": doc_lines,
        "original_amount_untaxed": doc._get_additional_amount()[0],
        "final_amount_untaxed": doc._get_additional_amount()[2],
        "adjust_amount_untaxed": doc._get_additional_amount()[2],
    }
    return d


def prepare_data_payment(doc):
    config_params = doc.env["ir.config_parameter"].sudo()

    # prepare lines information
    doc_lines = [
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
        for line in doc.tax_invoice_ids
    ]
    if not doc_lines:
        invoice = doc.reconciled_invoice_ids
        doc_lines = [
            {
                "product_code": "",
                "product_name": line.name and line.name.split(" ")[0] or "",
                "product_price": line.price_unit,
                "product_quantity": line.quantity,
                "line_tax_type_code": "FRE",
                "line_tax_rate": 0.0,
                "line_base_amount": line.price_subtotal,
                "line_tax_amount": 0.0,
                "line_total_amount": line.price_subtotal,
            }
            for line in invoice.invoice_line_ids
        ]

    partner = doc.partner_id

    d = {
        "currency_code": doc.currency_id.name,
        "document_type_code": doc.etax_doctype,
        "document_id": doc.name,
        "document_issue_dtm": doc.date and doc.date.strftime("%Y-%m-%dT%H:%M:%S"),
        # As of now, no use for payment
        "create_purpose_code": "",
        "create_purpose": "",
        "ref_document_id": "",
        "ref_document_issue_dtm": "",
        "ref_document_type_code": "",
        # --
        "buyer_ref_document": doc.ref,
        "seller_branch_id": doc._get_branch_id() or doc.company_id.branch,
        "source_system": config_params.get_param("web.base.url", ""),
        "send_mail": "Y"
        if config_params.get_param("frappe_etax_service.is_send_etax_email")
        else "N",
        "seller_tax_id": doc.company_id.vat,
        "buyer_name": partner.name,
        "buyer_type": "TXID",  # TXID, NIDN, CCPT, OTHR (no taxid)
        "buyer_tax_id": partner.vat,
        "buyer_branch_id": partner.branch or "00000",
        "buyer_email": partner.email,
        "buyer_zip": partner.zip,
        "buyer_building_name": "",
        "buyer_building_no": "",
        "buyer_address_line1": partner.street,
        "buyer_address_line2": partner.street2,
        "buyer_address_line3": "",
        "buyer_address_line4": "",
        "buyer_address_line5": "",
        "buyer_city_name": partner.city,
        "buyer_country_code": doc.partner_id.country_id
        and doc.partner_id.country_id.code
        or "",
        "line_item_information": doc_lines,
        # As of now, no use for payment
        "original_amount_untaxed": False,
        "final_amount_untaxed": False,
        "adjust_amount_untaxed": False,
    }
    return d
