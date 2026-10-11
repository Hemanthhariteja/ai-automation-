import csv
import io
import json
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.lead import Lead

LEAD_EXPORT_COLUMNS = [
    "id", "created_at", "source", "status", "priority",
    "customer_name", "customer_email", "customer_phone",
    "intent", "category", "confidence", "score",
    "raw_message", "extracted_data",
]

CUSTOMER_EXPORT_COLUMNS = ["id", "created_at", "name", "email", "phone", "lead_count"]


def _to_csv(rows: list[dict], columns: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def export_leads_to_csv(
    db: Session,
    business_id: int,
    status_filter: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
) -> str:
    query = db.query(Lead).filter(Lead.business_id == business_id)
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if priority:
        query = query.filter(Lead.priority == priority)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Lead.raw_message.ilike(like), Lead.intent.ilike(like)))

    leads = query.order_by(Lead.created_at.desc()).all()

    rows = [
        {
            "id": lead.id,
            "created_at": lead.created_at.isoformat() if lead.created_at else "",
            "source": lead.source,
            "status": lead.status,
            "priority": lead.priority,
            "customer_name": lead.customer.name if lead.customer else "",
            "customer_email": lead.customer.email if lead.customer else "",
            "customer_phone": lead.customer.phone if lead.customer else "",
            "intent": lead.intent or "",
            "category": lead.category or "",
            "confidence": lead.confidence if lead.confidence is not None else "",
            "score": lead.score if lead.score is not None else "",
            "raw_message": lead.raw_message or "",
            "extracted_data": json.dumps(lead.extracted_data) if lead.extracted_data else "",
        }
        for lead in leads
    ]
    return _to_csv(rows, LEAD_EXPORT_COLUMNS)


def export_customers_to_csv(db: Session, business_id: int) -> str:
    customers = (
        db.query(Customer)
        .filter(Customer.business_id == business_id)
        .order_by(Customer.created_at.desc())
        .all()
    )

    rows = [
        {
            "id": customer.id,
            "created_at": customer.created_at.isoformat() if customer.created_at else "",
            "name": customer.name or "",
            "email": customer.email or "",
            "phone": customer.phone or "",
            "lead_count": len(customer.leads),
        }
        for customer in customers
    ]
    return _to_csv(rows, CUSTOMER_EXPORT_COLUMNS)
