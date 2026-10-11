"""Seeds a demo "The Copper Spoon" restaurant business with ~20 synthetic leads.

Run from backend/: `python -m app.seed`

Idempotent: if a business already exists for the demo owner email, it exits
without creating duplicates. Leads are created through the real service
layer (get_or_create_customer, run_ai_pipeline_on_lead, trigger_workflows,
and — for a few, to show off the Messenger channel — ingest_channel_message)
so classification/scoring/workflow side-effects are genuine, not hand-faked —
then backdated across the last 30 days so the Analytics "leads over time"
chart has something to show. No real personal data — every name/email below
is fictional.
"""

import datetime
import random

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.channels.base import InboundMessage
from app.database.session import SessionLocal, init_db
from app.models.business import Business
from app.models.lead import Lead
from app.models.user import User
from app.models.workflow import Workflow, WorkflowExecution, WorkflowNode
from app.schemas.lead import LeadCustomerInfo
from app.services.channel_intake import ingest_channel_message
from app.services.customer_service import get_or_create_customer
from app.services.lead_ai import run_ai_pipeline_on_lead
from app.services.workflow_trigger import trigger_workflows
from app.workflows.templates import WORKFLOW_TEMPLATES

DEMO_OWNER_EMAIL = "owner@thecopperspoon.io"
DEMO_OWNER_PASSWORD = "demo12345"

# (message, name, email, phone) — delivered as web-form/manual leads.
DEMO_LEADS = [
    ("I'd like to book a table for 4 this Saturday at 7pm", "Priya Shah", "priya@customerdomain.io", None),
    ("Complaint: the food arrived cold and the service was really slow last night, very disappointed", "Raj Mehta", "raj@customerdomain.io", None),
    ("Can I get a quote for catering a corporate lunch for 30 people next Friday? Budget around $500", None, None, None),
    ("What are your hours on public holidays?", "Amit Kumar", "amit@customerdomain.io", "555-2211"),
    ("Do you have vegan or gluten-free options on the menu?", "Neha Verma", None, None),
    ("URGENT: we have a private party of 20 tonight, any chance you can fit us in?", "Sanjay Rao", "sanjay@customerdomain.io", None),
    ("I placed an online order over an hour ago and it still hasn't arrived, can someone help?", None, None, None),
    ("Looking to book the private dining room for an anniversary dinner next month, budget flexible", "Divya Nair", "divya@customerdomain.io", None),
    ("Complaint: found a hair in my food, this is unacceptable", "Karan Singh", "karan@customerdomain.io", None),
    ("Can I get a quote for buffet catering for a wedding, about 150 guests, budget $3000", "Meera Iyer", "meera@customerdomain.io", "555-7788"),
    ("Just wondering if you take walk-ins or do we need a reservation?", None, None, None),
    ("We'd like to reserve a table for 6 next Tuesday evening", "Arjun Patel", "arjun@customerdomain.io", None),
    ("My delivery order was missing an item, please advise", "Kavita Joshi", None, None),
    ("Interested in hosting a birthday party for my daughter, party of 15, this weekend if possible, urgent", "Ravi Desai", "ravi@customerdomain.io", None),
    ("Can you cater a drop-off lunch for our office, 25 people, tomorrow if possible", "Ananya Reddy", "ananya@customerdomain.io", "555-4433"),
    ("What's the price range for a private event booking?", None, None, None),
    ("Urgent: we've been waiting 45 minutes for our table despite having a reservation", "Vikram Malhotra", "vikram@customerdomain.io", None),
    ("Do you offer takeout containers for large orders?", "Sunita Rao", "sunita@customerdomain.io", None),
    ("We're planning a corporate event for 50 people next quarter, can you send catering info and pricing?", "Rahul Gupta", "rahul@customerdomain.io", None),
    ("Table for 2 tonight around 8pm if available", "Pooja Sharma", None, None),
]

# A few extra leads arriving via the Messenger channel (see app/channels/),
# to show that data source in the seeded Analytics/Leads view out of the box.
DEMO_MESSENGER_MESSAGES = [
    ("Hey! Saw your page — do you guys deliver to Koramangala?", "Instagram follower"),
    ("Can I book a table for 2 this Friday night?", "Aditi R"),
    ("Complaint: we messaged an hour ago about a wrong order and no one's replied yet", "Farhan K"),
]


def _random_recent_datetime(days_back: int) -> datetime.datetime:
    offset = datetime.timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - offset


def _ensure_demo_business(db: Session) -> tuple[Business, bool]:
    existing = db.query(User).filter(User.email == DEMO_OWNER_EMAIL).first()
    if existing is not None:
        return db.get(Business, existing.business_id), False

    business = Business(
        name="The Copper Spoon",
        slug="the-copper-spoon",
        description="The Copper Spoon is a neighborhood restaurant serving modern comfort food for dine-in, takeout, and private events.",
        services="Dine-in, takeout & delivery, private event catering, group reservations",
        hours="Tue-Sun 11am-10pm, closed Mondays",
        contact_email="hello@thecopperspoon.io",
        contact_phone="+91-9876543210",
        tone="friendly",
    )
    db.add(business)
    db.flush()

    owner = User(
        email=DEMO_OWNER_EMAIL,
        hashed_password=hash_password(DEMO_OWNER_PASSWORD),
        full_name="Copper Spoon Owner",
        role="owner",
        business_id=business.id,
    )
    db.add(owner)
    db.commit()
    return business, True


def _seed_workflows(db: Session, business: Business) -> None:
    if db.query(Workflow).filter(Workflow.business_id == business.id).count() > 0:
        return
    for template_id in ("complaint_priority", "high_score_alert", "auto_respond_and_followup"):
        template = WORKFLOW_TEMPLATES[template_id]
        workflow = Workflow(
            business_id=business.id,
            name=template["name"],
            description=template["description"],
            trigger_type=template["trigger_type"],
            is_active=True,
        )
        db.add(workflow)
        db.flush()
        for node_def in template["nodes"]:
            db.add(WorkflowNode(workflow_id=workflow.id, **node_def))
    db.commit()


def _backdate(db: Session, lead: Lead) -> None:
    backdated = _random_recent_datetime(days_back=29)
    lead.created_at = backdated
    lead.updated_at = backdated
    for execution in db.query(WorkflowExecution).filter(WorkflowExecution.lead_id == lead.id).all():
        execution.started_at = backdated
        execution.completed_at = backdated


def _seed_leads(db: Session, business: Business) -> int:
    if db.query(Lead).filter(Lead.business_id == business.id).count() > 0:
        return 0

    created = 0
    for message, name, email, phone in DEMO_LEADS:
        customer_info = None
        if name or email or phone:
            customer_info = LeadCustomerInfo(name=name, email=email, phone=phone)
        customer, _ = get_or_create_customer(db, business.id, customer_info)

        lead = Lead(
            business_id=business.id,
            customer_id=customer.id if customer else None,
            raw_message=message,
            source="web_form",
        )
        db.add(lead)
        db.flush()

        run_ai_pipeline_on_lead(db, business, lead)
        # The seeded "auto_respond_and_followup" workflow already drafts an AI
        # reply for every new_enquiry lead, so conversation threads are
        # populated without a redundant direct call here.
        trigger_workflows(db, business, lead, "new_enquiry")

        _backdate(db, lead)
        created += 1

    for index, (text, sender_name) in enumerate(DEMO_MESSENGER_MESSAGES):
        lead = ingest_channel_message(
            db, business, "messenger", InboundMessage(sender_external_id=f"demo-psid-{index}", text=text, sender_name=sender_name)
        )
        _backdate(db, lead)
        created += 1

    db.commit()
    return created


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        business, business_created = _ensure_demo_business(db)
        if not business_created:
            print(f"Demo business already exists (owner: {DEMO_OWNER_EMAIL}) — skipping, nothing changed.")
            return

        _seed_workflows(db, business)
        lead_count = _seed_leads(db, business)

        print("Seeded demo data for The Copper Spoon.")
        print(f"  Login: {DEMO_OWNER_EMAIL} / {DEMO_OWNER_PASSWORD}")
        print(f"  Leads created: {lead_count} ({len(DEMO_MESSENGER_MESSAGES)} via the Messenger channel)")
        print("  Workflows: complaint_priority, high_score_alert, auto_respond_and_followup")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
