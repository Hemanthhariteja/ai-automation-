import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { IconArrowLeft } from "../components/Icons";
import { PageLoading } from "../components/Loading";
import {
  getLead,
  updateLead,
  classifyLead,
  generateResponse,
  getConversation,
  summarizeConversation,
} from "../services/leads";

const TRACKING_LABELS = {
  utm_source: "Source",
  utm_medium: "Medium",
  utm_campaign: "Campaign",
  utm_term: "Term",
  utm_content: "Content",
  gclid: "Google Ads click ID",
  fbclid: "Meta Ads click ID",
  referrer: "Referrer",
};

function TrackingSummary({ tracking }) {
  const entries = Object.entries(TRACKING_LABELS)
    .map(([key, label]) => [label, tracking[key]])
    .filter(([, value]) => value);

  if (entries.length === 0) {
    return (
      <>
        <h2>Source &amp; attribution</h2>
        <p className="muted">Direct visit — no ad or campaign parameters on this submission.</p>
      </>
    );
  }

  return (
    <>
      <h2>Source &amp; attribution</h2>
      <dl className="kv-list">
        {entries.map(([label, value]) => (
          <span key={label} style={{ display: "contents" }}>
            <dt>{label}</dt>
            <dd className="truncate">{value}</dd>
          </span>
        ))}
      </dl>
    </>
  );
}

export default function LeadDetail() {
  const { id } = useParams();
  const [lead, setLead] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [leadData, convoData] = await Promise.all([getLead(id), getConversation(id)]);
    setLead(leadData);
    setConversation(convoData);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function withBusy(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!lead) return <PageLoading label="Loading lead..." />;

  return (
    <div>
      <Link to="/leads" className="back-link"><IconArrowLeft width={16} height={16} /> Back to leads</Link>
      <div className="page-header">
        <h1>Lead #{lead.id}</h1>
        <span className={`badge badge-${lead.priority}`}>{lead.priority} priority</span>
      </div>
      {error && <p className="form-error">{error}</p>}

      <div className="dashboard-columns">
        <section className="panel">
          <h2>Message</h2>
          <p>{lead.raw_message || <em>No message</em>}</p>

          {lead.tracking_data && <TrackingSummary tracking={lead.tracking_data} />}

          <h2>AI classification</h2>
          <dl className="kv-list">
            <dt>Intent</dt>
            <dd>{lead.intent || "-"}</dd>
            <dt>Category</dt>
            <dd>{lead.category || "-"}</dd>
            <dt>Confidence</dt>
            <dd>{lead.confidence != null ? `${Math.round(lead.confidence * 100)}%` : "-"}</dd>
            <dt>Score</dt>
            <dd>{lead.score ?? "-"} / 100</dd>
          </dl>

          <h2>Extracted info</h2>
          {lead.extracted_data ? (
            <dl className="kv-list">
              {Object.entries(lead.extracted_data).map(([key, value]) => (
                <span key={key} style={{ display: "contents" }}>
                  <dt>{key}</dt>
                  <dd>{value ?? <span className="muted">null</span>}</dd>
                </span>
              ))}
            </dl>
          ) : (
            <p className="muted">Not classified yet.</p>
          )}

          <button className="btn btn-secondary" disabled={busy} onClick={() => withBusy(() => classifyLead(id))}>
            Re-run AI classification
          </button>

          <h2 className="mt-section">Status &amp; priority</h2>
          <div className="form-row">
            <label>
              Status
              <select
                value={lead.status}
                disabled={busy}
                onChange={(e) => withBusy(() => updateLead(id, { status: e.target.value }))}
              >
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="won">Won</option>
                <option value="lost">Lost</option>
              </select>
            </label>
            <label>
              Priority
              <select
                value={lead.priority}
                disabled={busy}
                onChange={(e) => withBusy(() => updateLead(id, { priority: e.target.value }))}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
              </select>
            </label>
          </div>
        </section>

        <section className="panel">
          <h2>Conversation</h2>
          <ul className="conversation-list">
            {conversation?.messages.map((m) => (
              <li key={m.id} className={`message message-${m.sender}`}>
                <strong>{m.sender}:</strong> {m.content}
              </li>
            ))}
            {conversation?.messages.length === 0 && <p className="empty-state">No messages yet.</p>}
          </ul>
          {conversation?.summary && (
            <p className="summary-box">
              <strong>Summary:</strong> {conversation.summary}
            </p>
          )}
          <div className="button-row">
            <button className="btn btn-primary" disabled={busy} onClick={() => withBusy(() => generateResponse(id))}>
              Generate AI response
            </button>
            <button
              className="btn btn-secondary"
              disabled={busy}
              onClick={() => withBusy(() => summarizeConversation(id))}
            >
              Summarize conversation
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
