from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id
from app.database.session import get_db
from app.models.business import Business
from app.models.lead import Lead
from app.models.workflow import Workflow, WorkflowExecution, WorkflowNode
from app.schemas.workflow import (
    ConditionEvaluateRequest,
    ConditionEvaluateResponse,
    WorkflowCreate,
    WorkflowExecutionResponse,
    WorkflowNodeCreate,
    WorkflowNodeResponse,
    WorkflowNodeUpdate,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowTemplateSummary,
    WorkflowUpdate,
)
from app.workflows.engine import WorkflowEngine
from app.workflows.nodes import evaluate_condition
from app.workflows.templates import WORKFLOW_TEMPLATES

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _get_business(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def _get_owned_workflow(db: Session, business_id: int, workflow_id: int) -> Workflow:
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.business_id == business_id)
        .first()
    )
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return workflow


def _get_owned_node(workflow: Workflow, node_id: int) -> WorkflowNode:
    node = next((n for n in workflow.nodes if n.id == node_id), None)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    workflow = Workflow(
        business_id=business_id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        is_active=payload.is_active,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    return db.query(Workflow).filter(Workflow.business_id == business_id).order_by(Workflow.id).all()


@router.get("/templates", response_model=list[WorkflowTemplateSummary])
def list_templates():
    return [
        WorkflowTemplateSummary(id=key, name=t["name"], description=t["description"], trigger_type=t["trigger_type"])
        for key, t in WORKFLOW_TEMPLATES.items()
    ]


@router.post("/templates/{template_id}", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow_from_template(
    template_id: str,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Instantiates a ready-made rule as a normal, fully-editable workflow —
    nothing about the engine needs to know templates exist; it just sees
    another workflow with nodes. Adding a rule this way, or by hand via the
    node endpoints below, is equally additive."""
    template = WORKFLOW_TEMPLATES.get(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    workflow = Workflow(
        business_id=business_id,
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
    db.refresh(workflow)
    return workflow


@router.post("/evaluate-condition", response_model=ConditionEvaluateResponse)
def evaluate_condition_preview(
    payload: ConditionEvaluateRequest,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Checks a condition against a real lead without running a workflow —
    lets the future visual builder (and this API directly) test a rule
    before wiring it into a node."""
    lead = db.query(Lead).filter(Lead.id == payload.lead_id, Lead.business_id == business_id).first()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    try:
        passed, detail = evaluate_condition(lead, payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return ConditionEvaluateResponse(passed=passed, detail=detail)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: int, business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)
):
    return _get_owned_workflow(db, business_id, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    payload: WorkflowUpdate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workflow, field, value)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: int, business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    db.delete(workflow)
    db.commit()


@router.post("/{workflow_id}/nodes", response_model=WorkflowNodeResponse, status_code=status.HTTP_201_CREATED)
def add_node(
    workflow_id: int,
    payload: WorkflowNodeCreate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    node = WorkflowNode(
        workflow_id=workflow.id,
        node_type=payload.node_type,
        order_index=payload.order_index,
        config=payload.config,
        position_x=payload.position_x,
        position_y=payload.position_y,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.patch("/{workflow_id}/nodes/{node_id}", response_model=WorkflowNodeResponse)
def update_node(
    workflow_id: int,
    node_id: int,
    payload: WorkflowNodeUpdate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    node = _get_owned_node(workflow, node_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    db.commit()
    db.refresh(node)
    return node


@router.delete("/{workflow_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(
    workflow_id: int,
    node_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    node = _get_owned_node(workflow, node_id)
    db.delete(node)
    db.commit()


@router.post("/{workflow_id}/run", response_model=WorkflowExecutionResponse)
def run_workflow(
    workflow_id: int,
    payload: WorkflowRunRequest,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    lead = (
        db.query(Lead)
        .filter(Lead.id == payload.lead_id, Lead.business_id == business_id)
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    business = _get_business(db, business_id)

    execution = WorkflowEngine(db).execute(workflow, lead, business)
    db.commit()
    db.refresh(execution)
    return execution


@router.get("/{workflow_id}/executions", response_model=list[WorkflowExecutionResponse])
def list_executions(
    workflow_id: int, business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)
):
    workflow = _get_owned_workflow(db, business_id, workflow_id)
    return (
        db.query(WorkflowExecution)
        .filter(WorkflowExecution.workflow_id == workflow.id)
        .order_by(WorkflowExecution.id.desc())
        .all()
    )
