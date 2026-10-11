from pydantic import BaseModel


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class CategoryCount(BaseModel):
    label: str
    count: int


class ScoreDistribution(BaseModel):
    low: int
    medium: int
    high: int


class ProviderUsage(BaseModel):
    provider: str
    total_calls: int
    fallback_calls: int


class WorkflowPerformance(BaseModel):
    workflow_id: int
    workflow_name: str
    total_executions: int
    success_count: int
    failed_count: int


class AnalyticsOverview(BaseModel):
    leads_over_time: list[TimeSeriesPoint]
    leads_by_status: list[CategoryCount]
    leads_by_priority: list[CategoryCount]
    leads_by_intent: list[CategoryCount]
    score_distribution: ScoreDistribution
    provider_usage: list[ProviderUsage]
    workflow_performance: list[WorkflowPerformance]
