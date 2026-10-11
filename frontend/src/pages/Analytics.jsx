import { useEffect, useState } from "react";
import { getAnalyticsOverview } from "../services/analytics";
import { useColorScheme } from "../hooks/useColorScheme";
import LeadsOverTimeChart from "../components/charts/LeadsOverTimeChart";
import CategoryBarChart from "../components/charts/CategoryBarChart";
import StackedStatusBarChart from "../components/charts/StackedStatusBarChart";
import { ORDINAL, STATUS, intentColor, statusColor } from "../components/charts/palette";
import { PageLoading } from "../components/Loading";
import EmptyState from "../components/EmptyState";
import { IconAnalytics } from "../components/Icons";

const PRIORITY_ORDER = ["low", "normal", "high"];
const SCORE_ORDER = ["low", "medium", "high"];

function ChartPanel({ title, description, empty, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {description && <p className="section-intro">{description}</p>}
      {empty ? <EmptyState Icon={IconAnalytics} text="Not enough data yet." /> : children}
    </section>
  );
}

export default function Analytics() {
  const scheme = useColorScheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAnalyticsOverview()
      .then(setData)
      .catch(() => setError("Could not load analytics data"));
  }, []);

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <PageLoading label="Loading analytics..." />;

  const priorityData = PRIORITY_ORDER.map((label) => ({
    label,
    count: data.leads_by_priority.find((c) => c.label === label)?.count || 0,
  }));

  const scoreData = SCORE_ORDER.map((label) => ({ label, count: data.score_distribution[label] }));

  const providerData = data.provider_usage.map((p) => ({
    provider: p.provider,
    direct: p.total_calls - p.fallback_calls,
    fallback: p.fallback_calls,
  }));

  const workflowData = data.workflow_performance.map((w) => ({
    name: w.workflow_name,
    success_count: w.success_count,
    failed_count: w.failed_count,
  }));

  const priorityColorFor = (label) => {
    const index = PRIORITY_ORDER.indexOf(label);
    return ORDINAL[scheme][index] ?? ORDINAL[scheme][0];
  };
  const scoreColorFor = (label) => {
    const index = SCORE_ORDER.indexOf(label);
    return ORDINAL[scheme][index] ?? ORDINAL[scheme][0];
  };

  return (
    <div>
      <h1>Analytics</h1>
      <p className="page-intro">
        Last 30 days, this business only. Lead scoring is a heuristic based on legible factors (intent, budget,
        urgency, completeness) — not a validated statistical model.
      </p>

      <ChartPanel title="Leads over time" description="New leads per day, last 30 days." empty={data.leads_over_time.length === 0}>
        <LeadsOverTimeChart data={data.leads_over_time} scheme={scheme} />
      </ChartPanel>

      <div className="dashboard-columns">
        <ChartPanel title="Leads by status" empty={data.leads_by_status.length === 0}>
          <CategoryBarChart data={data.leads_by_status} colorFor={(l) => statusColor(l, scheme)} scheme={scheme} />
        </ChartPanel>

        <ChartPanel title="Leads by priority" empty={priorityData.every((d) => d.count === 0)}>
          <CategoryBarChart data={priorityData} colorFor={priorityColorFor} scheme={scheme} />
        </ChartPanel>

        <ChartPanel title="Leads by intent" empty={data.leads_by_intent.length === 0}>
          <CategoryBarChart data={data.leads_by_intent} colorFor={(l) => intentColor(l, scheme)} scheme={scheme} />
        </ChartPanel>

        <ChartPanel
          title="Score distribution"
          description="0-30 low, 31-70 medium, 71-100 high"
          empty={scoreData.every((d) => d.count === 0)}
        >
          <CategoryBarChart data={scoreData} colorFor={scoreColorFor} scheme={scheme} />
        </ChartPanel>
      </div>

      <ChartPanel
        title="AI provider usage"
        description="Which provider actually served each AI call, and how often it needed to fall back."
        empty={providerData.length === 0}
      >
        <StackedStatusBarChart
          data={providerData}
          xKey="provider"
          goodKey="direct"
          badKey="fallback"
          goodLabel="Served directly"
          badLabel="Served via fallback"
          badColor={STATUS.warning}
          scheme={scheme}
        />
      </ChartPanel>

      <ChartPanel title="Workflow performance" description="Execution outcomes per workflow." empty={workflowData.length === 0}>
        <StackedStatusBarChart
          data={workflowData}
          xKey="name"
          goodKey="success_count"
          badKey="failed_count"
          goodLabel="Success"
          badLabel="Failed"
          badColor={STATUS.critical}
          scheme={scheme}
        />
      </ChartPanel>
    </div>
  );
}
