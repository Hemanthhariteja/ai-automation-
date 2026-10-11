import logging

from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.lead import Lead
from app.models.workflow import Workflow
from app.workflows.engine import WorkflowEngine

logger = logging.getLogger(__name__)


def trigger_workflows(db: Session, business: Business, lead: Lead, trigger_type: str) -> None:
    """Fires every active workflow of the given trigger type against a lead.
    Each workflow runs independently — one failing must never stop the
    others, and none of them may ever propagate an exception back to the
    caller (lead creation must always succeed regardless of workflow state)."""
    workflows = (
        db.query(Workflow)
        .filter(
            Workflow.business_id == business.id,
            Workflow.trigger_type == trigger_type,
            Workflow.is_active.is_(True),
        )
        .all()
    )

    engine = WorkflowEngine(db)
    for workflow in workflows:
        try:
            engine.execute(workflow, lead, business)
        except Exception:
            logger.exception("Workflow %s failed to execute for lead %s", workflow.id, lead.id)
