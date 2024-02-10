import pdfkit
from src.config.settings import TEMPLATE_ENV
from src.utils.convertors import get_base64_string


def generate_invoice_pdf(invoice_data: dict, pdf_options: dict, template: str):
    tax_amount = invoice_data["amount"] * (invoice_data["tax"] / 100)
    total_amount = invoice_data["amount"] + tax_amount

    status = "CANCELLED"
    status_color = "gray"
    if invoice_data["dueBy"]:
        if invoice_data["paidOn"]:
            status = "PAID"
            status_color = "green"
        else:
            status = "GENERATED"
            status_color = "indigo"
    invoice_data["status"] = status
    invoice_data["status_color"] = status_color
    logo = get_base64_string("src/assets/logo-full.png")
    template = TEMPLATE_ENV.get_template(template)
    output_text = template.render(
        logo=logo, tax_amount=tax_amount, total_amount=total_amount, **invoice_data
    )
    pdf = pdfkit.from_string(output_text, False, options=pdf_options)
    return pdf


def generate_timesheet_pdf(
    data: dict,
    pdf_options: dict,
    template: str,
):
    logo = get_base64_string("src/assets/logo-full.png")
    template = TEMPLATE_ENV.get_template(template)
    output_text = template.render(
        logo=logo,
        data=data,
    )
    pdf = pdfkit.from_string(output_text, False, options=pdf_options)
    return pdf
