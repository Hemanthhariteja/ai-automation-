import datetime
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id
from app.database.session import get_db
from app.models.ai_log import AILog
from app.models.lead import Lead
from app.models.workflow import Workflow, WorkflowExecution
from app.schemas.analytics import (
    AnalyticsOverview,
    CategoryCount,
    ProviderUsage,
    ScoreDistribution,
    TimeSeriesPoint,
    WorkflowPerformance,
)
from app.utils.time import utcnow

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

ANALYTICS_WINDOW_DAYS = 30


def _leads_over_time(db: Session, business_id: int) -> list[TimeSeriesPoint]:
    cutoff = utcnow().replace(tzinfo=None) - datetime.timedelta(days=ANALYTICS_WINDOW_DAYS)
    rows = (
        db.query(func.date(Lead.created_at).label("day"), func.count(Lead.id))
        .filter(Lead.business_id == business_id, Lead.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [TimeSeriesPoint(date=str(day), count=count) for day, count in rows]


def _leads_by_field(db: Session, business_id: int, field, unclassified_label: str) -> list[CategoryCount]:
    rows = db.query(field, func.count(Lead.id)).filter(Lead.business_id == business_id).group_by(field).all()
    return [CategoryCount(label=value or unclassified_label, count=count) for value, count in rows]


def _score_distribution(db: Session, business_id: int) -> ScoreDistribution:
    base = db.query(Lead).filter(Lead.business_id == business_id, Lead.score.isnot(None))
    return ScoreDistribution(
        low=base.filter(Lead.score <= 30).count(),
        medium=base.filter(Lead.score > 30, Lead.score <= 70).count(),
        high=base.filter(Lead.score > 70).count(),
    )


def _provider_usage(db: Session, business_id: int) -> list[ProviderUsage]:
    logs = (
        db.query(AILog.actual_provider, AILog.fallback_used)
        .filter(AILog.business_id == business_id, AILog.success.is_(True))
        .all()
    )
    counts: dict[str, dict[str, int]] = {}
    for provider, fallback_used in logs:
        entry = counts.setdefault(provider, {"total": 0, "fallback": 0})
        entry["total"] += 1
        if fallback_used:
            entry["fallback"] += 1
    return [
        ProviderUsage(provider=provider, total_calls=v["total"], fallback_calls=v["fallback"])
        for provider, v in counts.items()
    ]


def _workflow_performance(db: Session, business_id: int) -> list[WorkflowPerformance]:
    workflows = db.query(Workflow).filter(Workflow.business_id == business_id).all()
    performance = []
    for wf in workflows:
        statuses = [
            status
            for (status,) in db.query(WorkflowExecution.status).filter(WorkflowExecution.workflow_id == wf.id).all()
        ]
        if not statuses:
            continue
        tally = Counter(statuses)
        performance.append(
            WorkflowPerformance(
                workflow_id=wf.id,
                workflow_name=wf.name,
                total_executions=len(statuses),
                success_count=tally.get("success", 0),
                failed_count=tally.get("failed", 0),
            )
        )
    return performance


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    return AnalyticsOverview(
        leads_over_time=_leads_over_time(db, business_id),
        leads_by_status=_leads_by_field(db, business_id, Lead.status, "unknown"),
        leads_by_priority=_leads_by_field(db, business_id, Lead.priority, "unset"),
        leads_by_intent=_leads_by_field(db, business_id, Lead.intent, "unclassified"),
        score_distribution=_score_distribution(db, business_id),
        provider_usage=_provider_usage(db, business_id),
        workflow_performance=_workflow_performance(db, business_id),
    )
