from typing import Dict
from datetime import datetime
import requests
import io
from fastapi import UploadFile
import tempfile
from pydantic import EmailStr
from fastapi_mail import FastMail, MessageSchema

from src.config.settings import billing_email_conf


def create_temp_file_from_bytes(file_bytes, filename):
    return UploadFile(file=io.BytesIO(file_bytes), filename=filename)


async def send_email(message: MessageSchema, template_name: str):
    fm = FastMail(billing_email_conf)
    try:
        await fm.send_message(message, template_name=template_name)
        return True
    except Exception as e:
        print("Hii")
        print(e)
        return False


async def send_timesheet(
    to_list: list, cc_list: list, report: bytes, template_data: dict
) -> bool:
    pdf_file: UploadFile = create_temp_file_from_bytes(report, "file.pdf")
    attachments = [
        {
            "file": pdf_file,
            "headers": {
                "Content-ID": "<attached_pdf@fastapi-mail>",
                "Content-Disposition": 'attachment; filename="timesheet.pdf"',
            },
            "mime_type": "application",
            "mime_subtype": "pdf",
        }
    ]
    message = MessageSchema(
        subject=f"Monthly Timesheet ({template_data['start_date']} - {template_data['end_date']})",
        recipients=to_list,
        cc=cc_list,
        template_body=template_data,
        attachments=attachments,
    )
    return await send_email(message, "timesheet_share.html")


async def send_invoice(
    to_list: list, cc_list: list, report: bytes, template_data: dict
) -> bool:
    pdf_file: UploadFile = create_temp_file_from_bytes(report, "file.pdf")
    attachments = [
        {
            "file": pdf_file,
            "headers": {
                "Content-ID": "<attached_pdf@fastapi-mail>",
                "Content-Disposition": f'attachment; filename="{template_data["invoice_number"]}.pdf"',
            },
            "mime_type": "application",
            "mime_subtype": "pdf",
        }
    ]
    message = MessageSchema(
        subject=f"GoApp Solutions | Invoice({(template_data['invoicePeriodStart'].strftime('%B %d, %Y'))} - {template_data['invoicePeriodStart'].strftime('%B %d, %Y')})",
        recipients=to_list,
        cc=cc_list,
        template_body=template_data,
        attachments=attachments,
    )
    return await send_email(message, "invoice_share.html")


async def send_test_mail(email):
    html = """<p>Hi this test mail, thanks for using Fastapi-mail</p> """

    message = MessageSchema(
        subject="Fastapi-Mail module", recipients=[email], body=html
    )

    fm = FastMail(billing_email_conf)
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(e)
        return False


async def send_attachment_test_mail(email, file):
    html = """<p>Hi this test mail, thanks for using Fastapi-mail</p> """
    pdf_file: UploadFile = create_temp_file_from_bytes(file, "file.pdf")
    attachments = [
        {
            "file": pdf_file,
            "headers": {
                "Content-ID": "<attached_pdf@fastapi-mail>",
                "Content-Disposition": 'attachment; filename="timesheet.pdf"',
            },
            "mime_type": "application",
            "mime_subtype": "pdf",
        }
    ]
    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=[email],
        body=html,
        attachments=attachments,
        template_body={},
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(e)
        return False
