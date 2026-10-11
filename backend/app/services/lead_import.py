import csv
import io

from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.lead import Lead
from app.schemas.lead import LeadCustomerInfo, LeadImportRowError, LeadImportSummary
from app.services.customer_service import get_or_create_customer
from app.services.lead_ai import run_ai_pipeline_on_lead
from app.services.workflow_trigger import trigger_workflows

MAX_IMPORT_ROWS = 500

# A row may use either header naming — flexible for whatever a spreadsheet export used.
MESSAGE_KEYS = ("message", "raw_message", "enquiry", "notes")
NAME_KEYS = ("name", "customer_name", "full_name")
EMAIL_KEYS = ("email", "customer_email")
PHONE_KEYS = ("phone", "customer_phone", "phone_number")


class ImportTooLargeError(Exception):
    pass


class ImportFormatError(Exception):
    pass


def _first_present(row: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return None


def parse_csv_rows(raw_bytes: bytes) -> list[dict]:
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportFormatError(f"Could not read file as UTF-8 text: {exc}")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ImportFormatError("CSV has no header row")

    normalized_fieldnames = [f.strip().lower() for f in reader.fieldnames]
    if not any(key in normalized_fieldnames for key in MESSAGE_KEYS):
        raise ImportFormatError(
            f"CSV must have a message column — one of: {', '.join(MESSAGE_KEYS)}"
        )

    rows = []
    for row in reader:
        normalized = {(k or "").strip().lower(): v for k, v in row.items()}
        rows.append(normalized)

    if len(rows) > MAX_IMPORT_ROWS:
        raise ImportTooLargeError(f"CSV has {len(rows)} rows — the limit is {MAX_IMPORT_ROWS} per import")

    return rows


def import_leads_from_csv(db: Session, business: Business, raw_bytes: bytes) -> LeadImportSummary:
    rows = parse_csv_rows(raw_bytes)

    imported = 0
    errors: list[LeadImportRowError] = []

    for index, row in enumerate(rows, start=1):
        message = _first_present(row, MESSAGE_KEYS)
        if not message:
            errors.append(LeadImportRowError(row=index, reason="Missing message"))
            continue

        name = _first_present(row, NAME_KEYS)
        email = _first_present(row, EMAIL_KEYS)
        phone = _first_present(row, PHONE_KEYS)

        customer_info = LeadCustomerInfo(name=name, email=email, phone=phone) if (name or email or phone) else None
        customer, _ = get_or_create_customer(db, business.id, customer_info)

        lead = Lead(
            business_id=business.id,
            customer_id=customer.id if customer else None,
            raw_message=message[:4000],
            source="import",
        )
        db.add(lead)
        db.flush()

        run_ai_pipeline_on_lead(db, business, lead)
        trigger_workflows(db, business, lead, "new_enquiry")
        imported += 1

    db.commit()

    return LeadImportSummary(total_rows=len(rows), imported=imported, skipped=len(errors), errors=errors)
