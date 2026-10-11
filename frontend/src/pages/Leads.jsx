import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  createLead,
  downloadBlob,
  exportCustomersCsv,
  exportLeadsCsv,
  importLeadsCsv,
  importTemplateUrl,
  listLeads,
} from "../services/leads";
import { PageLoading } from "../components/Loading";
import EmptyState from "../components/EmptyState";
import { IconLeads } from "../components/Icons";

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [importSummary, setImportSummary] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [exporting, setExporting] = useState("");
  const fileInputRef = useRef(null);

  async function load() {
    const params = {};
    if (statusFilter) params.status = statusFilter;
    const data = await listLeads(params);
    setLeads(data.items);
    setTotal(data.total);
    setLoaded(true);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const payload = { raw_message: message, source: "web_form" };
      if (customerEmail || customerName) {
        payload.customer = { email: customerEmail || null, name: customerName || null };
      }
      await createLead(payload);
      setMessage("");
      setCustomerEmail("");
      setCustomerName("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not submit enquiry");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFileSelected(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportError("");
    setImportSummary(null);
    try {
      const summary = await importLeadsCsv(file);
      setImportSummary(summary);
      await load();
    } catch (err) {
      setImportError(err.response?.data?.detail || "Could not import this file");
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  }

  async function handleExportLeads() {
    setExporting("leads");
    try {
      const params = statusFilter ? { status: statusFilter } : {};
      const blob = await exportLeadsCsv(params);
      downloadBlob(blob, "leads_export.csv");
    } finally {
      setExporting("");
    }
  }

  async function handleExportCustomers() {
    setExporting("customers");
    try {
      const blob = await exportCustomersCsv();
      downloadBlob(blob, "customers_export.csv");
    } finally {
      setExporting("");
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Leads ({total})</h1>
        <div className="header-actions">
          <a href={importTemplateUrl()} className="btn btn-secondary" download>
            Download CSV template
          </a>
          <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()} disabled={importing}>
            {importing ? "Importing..." : "Import CSV"}
          </button>
          <input ref={fileInputRef} type="file" accept=".csv" hidden onChange={handleFileSelected} />
          <button className="btn btn-secondary" onClick={handleExportLeads} disabled={exporting !== ""}>
            {exporting === "leads" ? "Exporting..." : "Export leads CSV"}
          </button>
          <button className="btn btn-secondary" onClick={handleExportCustomers} disabled={exporting !== ""}>
            {exporting === "customers" ? "Exporting..." : "Export customers CSV"}
          </button>
          <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "Submit new enquiry"}
          </button>
        </div>
      </div>

      {importError && <p className="form-error">{importError}</p>}
      {importSummary && (
        <div className="panel">
          <h2>Import result</h2>
          <p>
            {importSummary.imported} of {importSummary.total_rows} rows imported
            {importSummary.skipped > 0 && `, ${importSummary.skipped} skipped`}.
          </p>
          {importSummary.errors.length > 0 && (
            <ul className="simple-list">
              {importSummary.errors.map((e) => (
                <li key={e.row} className="muted">
                  Row {e.row}: {e.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {showForm && (
        <form className="panel" onSubmit={handleSubmit}>
          {error && <p className="form-error">{error}</p>}
          <label>
            Message
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              required
              placeholder="e.g. I need a quote for a new website, budget $2000, fairly urgent"
            />
          </label>
          <div className="form-row">
            <label>
              Customer name (optional)
              <input value={customerName} onChange={(e) => setCustomerName(e.target.value)} />
            </label>
            <label>
              Customer email (optional)
              <input type="email" value={customerEmail} onChange={(e) => setCustomerEmail(e.target.value)} />
            </label>
          </div>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit enquiry"}
          </button>
        </form>
      )}

      <div className="filter-row">
        <label>
          Status
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="won">Won</option>
            <option value="lost">Lost</option>
          </select>
        </label>
      </div>

      {!loaded ? (
        <PageLoading label="Loading leads..." />
      ) : leads.length === 0 ? (
        <EmptyState
          Icon={IconLeads}
          text={statusFilter ? "No leads match this filter." : "No leads yet — submit an enquiry to get started."}
        />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Message</th>
              <th>Intent</th>
              <th>Score</th>
              <th>Priority</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id}>
                <td>
                  <Link to={`/leads/${lead.id}`}>
                    {lead.customer?.name || lead.customer?.email || `Lead #${lead.id}`}
                  </Link>
                </td>
                <td className="truncate">{lead.raw_message}</td>
                <td>{lead.intent || "-"}</td>
                <td>{lead.score ?? "-"}</td>
                <td>
                  <span className={`badge badge-${lead.priority}`}>{lead.priority}</span>
                </td>
                <td>{lead.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
