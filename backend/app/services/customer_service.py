from typing import Optional

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.lead import LeadCustomerInfo


def get_or_create_customer(
    db: Session, business_id: int, info: Optional[LeadCustomerInfo]
) -> tuple[Optional[Customer], bool]:
    """Find an existing customer by email within the business, or create one.
    Without an email there's no reliable key to dedupe on, so a new row is
    created for each lead — acceptable for the MVP, revisit if this becomes
    a real pain point. Returns (customer, was_newly_created) — the flag is
    what drives the workflow engine's "new_customer" trigger."""

    if info is None or not (info.name or info.email or info.phone):
        return None, False

    if info.email:
        existing = (
            db.query(Customer)
            .filter(Customer.business_id == business_id, Customer.email == info.email)
            .first()
        )
        if existing is not None:
            if info.name and not existing.name:
                existing.name = info.name
            if info.phone and not existing.phone:
                existing.phone = info.phone
            return existing, False

    customer = Customer(business_id=business_id, name=info.name, email=info.email, phone=info.phone)
    db.add(customer)
    db.flush()
    return customer, True
