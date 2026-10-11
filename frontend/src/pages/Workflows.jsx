import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createWorkflow, createFromTemplate, listTemplates, listWorkflows } from "../services/workflows";
import { PageLoading } from "../components/Loading";
import EmptyState from "../components/EmptyState";
import { IconWorkflow } from "../components/Icons";

export default function Workflows() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState("new_enquiry");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [wf, tpl] = await Promise.all([listWorkflows(), listTemplates()]);
    setWorkflows(wf);
    setTemplates(tpl);
    setLoaded(true);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const workflow = await createWorkflow({ name, trigger_type: triggerType, is_active: true });
      navigate(`/workflows/${workflow.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create workflow");
    } finally {
      setBusy(false);
    }
  }

  async function handleUseTemplate(templateId) {
    setBusy(true);
    setError("");
    try {
      const workflow = await createFromTemplate(templateId);
      navigate(`/workflows/${workflow.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create workflow from template");
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return <PageLoading label="Loading workflows..." />;

  return (
    <div>
      <div className="page-header">
        <h1>Workflows</h1>
        <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New workflow"}
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}

      {showForm && (
        <form className="panel" onSubmit={handleCreate}>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Trigger
            <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
              <option value="new_enquiry">New enquiry</option>
              <option value="new_customer">New customer</option>
              <option value="manual">Manual</option>
              <option value="scheduled">Scheduled</option>
            </select>
          </label>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Create and add nodes
          </button>
        </form>
      )}

      <section className="panel">
        <h2>Start from a template</h2>
        <div className="template-grid">
          {templates.map((t) => (
            <div key={t.id} className="template-card">
              <h3>{t.name}</h3>
              <p className="muted">{t.description}</p>
              <button className="btn btn-sm btn-secondary" disabled={busy} onClick={() => handleUseTemplate(t.id)}>
                Use this template
              </button>
            </div>
          ))}
        </div>
      </section>

      {workflows.length === 0 ? (
        <EmptyState Icon={IconWorkflow} text="No workflows yet — create one above or start from a template." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Trigger</th>
              <th>Active</th>
              <th>Nodes</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((wf) => (
              <tr key={wf.id}>
                <td>
                  <Link to={`/workflows/${wf.id}`}>{wf.name}</Link>
                </td>
                <td>{wf.trigger_type}</td>
                <td>{wf.is_active ? "Yes" : "No"}</td>
                <td>{wf.nodes.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
