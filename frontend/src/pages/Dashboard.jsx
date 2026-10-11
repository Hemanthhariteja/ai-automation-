import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboardSummary } from "../services/dashboard";
import { IconAnalytics, IconBell, IconLeads, IconTask } from "../components/Icons";
import { PageLoading } from "../components/Loading";
import EmptyState from "../components/EmptyState";

function StatCard({ label, value, Icon, variant }) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <div className="stat-value">{value}</div>
        <span className={`stat-icon${variant ? ` stat-icon-${variant}` : ""}`}>
          <Icon width={16} height={16} />
        </span>
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch(() => setError("Could not load dashboard data"));
  }, []);

  if (error) return <p className="form-error">{error}</p>;
  if (!summary) return <PageLoading label="Loading dashboard..." />;

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <Link to="/leads" className="btn btn-primary">Submit new enquiry</Link>
      </div>

      <div className="stat-grid">
        <StatCard label="Total leads" value={summary.total_leads} Icon={IconLeads} />
        <StatCard label="New leads" value={summary.new_leads} Icon={IconLeads} />
        <StatCard label="High priority" value={summary.high_priority_leads} Icon={IconAnalytics} variant="danger" />
        <StatCard label="Last 7 days" value={summary.leads_last_7_days} Icon={IconAnalytics} />
        <StatCard label="Unread notifications" value={summary.unread_notifications} Icon={IconBell} variant="warning" />
        <StatCard label="Open tasks" value={summary.open_tasks} Icon={IconTask} variant="success" />
      </div>

      <div className="dashboard-columns">
        <section className="panel">
          <h2>Recent leads</h2>
          {summary.recent_leads.length === 0 ? (
            <EmptyState Icon={IconLeads} text="No leads yet." />
          ) : (
            <ul className="simple-list">
              {summary.recent_leads.map((lead) => (
                <li key={lead.id}>
                  <Link to={`/leads/${lead.id}`}>
                    {lead.customer?.name || lead.customer?.email || `Lead #${lead.id}`}
                  </Link>
                  <span className={`badge badge-${lead.priority}`}>{lead.priority}</span>
                  <span className="muted">{lead.intent || "unclassified"}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h2>Notifications</h2>
          {summary.recent_notifications.length === 0 ? (
            <EmptyState Icon={IconBell} text="No notifications yet." />
          ) : (
            <ul className="simple-list">
              {summary.recent_notifications.map((n) => (
                <li key={n.id} className={n.is_read ? "read" : "unread"}>
                  {n.message}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h2>Open tasks</h2>
          {summary.recent_tasks.length === 0 ? (
            <EmptyState Icon={IconTask} text="No open tasks." />
          ) : (
            <ul className="simple-list">
              {summary.recent_tasks.map((t) => (
                <li key={t.id}>{t.title}</li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
