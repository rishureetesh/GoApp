import os
from pathlib import Path
import jinja2
from datetime import datetime
from fastapi_mail import ConnectionConfig


STORAGE_ACCOUNT_NAME = os.environ.get("STORAGE_ACCOUNT_NAME")

# AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
# AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
# AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")

GST_PCT = int(os.getenv("GST_PCT", "18"))

ORG_START_DATE = os.getenv("ORG_START_DATE", "2023-05-31")

CUT_OFF_DATE = datetime.strptime(ORG_START_DATE, "%Y-%m-%d")

TEMPLATE_LOADER = jinja2.FileSystemLoader(searchpath="./src")
TEMPLATE_ENV = jinja2.Environment(loader=TEMPLATE_LOADER)

BILLING_MAIL_USERNAME = os.getenv("BILLING_MAIL_USERNAME", "rishu@gmail.com")
SALES_MAIL_USERNAME = os.getenv("BILLING_MAIL_USERNAME", "rishu@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "rishu@gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "80"))
MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Reetesh")

billing_email_conf = ConnectionConfig(
    MAIL_USERNAME=BILLING_MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=BILLING_MAIL_USERNAME,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=Path(__file__).parent / "email_templates",
)
