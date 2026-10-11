import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app import models


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_full_relationship_graph(db):
    business = models.Business(name="TechFix Solutions", slug="techfix-solutions", tone="friendly")
    db.add(business)
    db.flush()

    owner = models.User(
        email="owner@techfix.test",
        hashed_password="not-a-real-hash",
        full_name="Techfix Owner",
        role="owner",
        business_id=business.id,
    )
    customer = models.Customer(business_id=business.id, name="Jane Doe", email="jane@example.com")
    db.add_all([owner, customer])
    db.flush()

    lead = models.Lead(
        business_id=business.id,
        customer_id=customer.id,
        raw_message="Need a website redesign quote",
        intent="quote_request",
        confidence=0.87,
        extracted_data={"budget": None, "urgency": "high"},
        score=72,
        score_breakdown={"intent": 30, "urgency": 42},
        status="new",
        priority="high",
    )
    db.add(lead)
    db.flush()

    conversation = models.Conversation(business_id=business.id, customer_id=customer.id, lead_id=lead.id)
    db.add(conversation)
    db.flush()

    message = models.Message(conversation_id=conversation.id, sender="customer", content="Hi, need a quote")
    db.add(message)

    workflow = models.Workflow(business_id=business.id, name="New enquiry handler")
    db.add(workflow)
    db.flush()

    node = models.WorkflowNode(workflow_id=workflow.id, node_type="trigger", order_index=0)
    db.add(node)

    execution = models.WorkflowExecution(workflow_id=workflow.id, lead_id=lead.id, status="success")
    db.add(execution)

    task = models.Task(business_id=business.id, lead_id=lead.id, title="Follow up with Jane")
    db.add(task)

    notification = models.Notification(business_id=business.id, type="high_priority_lead", message="New high-priority lead")
    db.add(notification)

    ai_log = models.AILog(
        business_id=business.id,
        lead_id=lead.id,
        operation="classify",
        requested_provider="demo",
        actual_provider="demo",
        fallback_used=False,
    )
    db.add(ai_log)
    db.commit()

    # relationship traversal
    assert owner.business.name == "TechFix Solutions"
    assert business.users[0].email == "owner@techfix.test"
    assert lead.customer.name == "Jane Doe"
    assert lead.business.id == business.id
    assert conversation.messages[0].content == "Hi, need a quote"
    assert workflow.nodes[0].node_type == "trigger"
    assert workflow.executions[0].lead_id == lead.id
    assert task.lead.id == lead.id
    assert business.notifications[0].type == "high_priority_lead"
    assert business.ai_logs[0].operation == "classify"

    # null-by-default extraction fields stay null, never invented
    assert lead.extracted_data["budget"] is None
