import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TriggerType = Literal["new_enquiry", "new_customer", "manual", "scheduled"]
NodeType = Literal["trigger", "ai_processor", "condition", "action", "notification", "db", "end"]


class WorkflowNodeCreate(BaseModel):
    node_type: NodeType
    order_index: int = 0
    config: Optional[dict] = None
    position_x: float = 0
    position_y: float = 0


class WorkflowNodeUpdate(BaseModel):
    order_index: Optional[int] = None
    config: Optional[dict] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    node_type: str
    order_index: int
    config: Optional[dict]
    position_x: float
    position_y: float


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    trigger_type: TriggerType = "new_enquiry"
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    trigger_type: Optional[TriggerType] = None
    is_active: Optional[bool] = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    description: Optional[str]
    trigger_type: str
    is_active: bool
    nodes: list[WorkflowNodeResponse]


class WorkflowRunRequest(BaseModel):
    lead_id: int


class WorkflowExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    lead_id: Optional[int]
    status: str
    log: Optional[dict]
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime]


class WorkflowTemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    trigger_type: str


class ConditionEvaluateRequest(BaseModel):
    lead_id: int
    config: dict


class ConditionEvaluateResponse(BaseModel):
    passed: bool
    detail: str
