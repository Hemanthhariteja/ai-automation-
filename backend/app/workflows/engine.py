from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.lead import Lead
from app.models.workflow import Workflow, WorkflowExecution
from app.utils.time import utcnow
from app.workflows.nodes import NODE_HANDLERS


class WorkflowEngine:
    """Walks a workflow's nodes in order, running each one's handler and
    recording every step to the execution log. A condition that isn't met
    stops the remaining nodes (status "halt") without that being an error —
    only an actual handler failure marks the execution "failed". Never
    raises: node exceptions are caught and logged as a failed step so a
    broken workflow can never take down the request that triggered it."""

    def __init__(self, db: Session):
        self.db = db

    def execute(self, workflow: Workflow, lead: Lead, business: Business) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_id=workflow.id, lead_id=lead.id, status="running", log={"steps": []}
        )
        self.db.add(execution)
        self.db.flush()

        steps = []
        overall_status = "success"

        for node in sorted(workflow.nodes, key=lambda n: n.order_index):
            handler = NODE_HANDLERS.get(node.node_type)
            if handler is None:
                steps.append(
                    {"node_id": node.id, "node_type": node.node_type, "status": "skipped", "detail": "Unknown node type"}
                )
                continue

            try:
                result = handler(self.db, business, lead, node.config or {})
            except Exception as exc:  # a node handler bug must never crash the caller
                steps.append(
                    {"node_id": node.id, "node_type": node.node_type, "status": "failed", "detail": f"Unhandled error: {exc}"}
                )
                overall_status = "failed"
                break

            steps.append(
                {"node_id": node.id, "node_type": node.node_type, "status": result.status, "detail": result.detail}
            )
            if result.status == "failed":
                overall_status = "failed"
                break
            if result.status == "halt":
                break

        execution.status = overall_status
        execution.log = {"steps": steps}
        execution.completed_at = utcnow()
        self.db.flush()
        return execution
