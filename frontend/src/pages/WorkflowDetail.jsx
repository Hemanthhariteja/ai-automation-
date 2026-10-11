import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  addNode,
  deleteNode,
  deleteWorkflow,
  getWorkflow,
  listExecutions,
  runWorkflow,
  updateNode,
  updateWorkflow,
} from "../services/workflows";
import NodeCard from "../components/workflow/NodeCard";
import NodeForm from "../components/workflow/NodeForm";
import { IconArrowLeft } from "../components/Icons";
import { PageLoading } from "../components/Loading";

export default function WorkflowDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [formMode, setFormMode] = useState(null); // null | "add" | node.id being edited
  const [leadId, setLeadId] = useState("");
  const [runResult, setRunResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [wf, execs] = await Promise.all([getWorkflow(id), listExecutions(id)]);
    setWorkflow(wf);
    setExecutions(execs);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const sortedNodes = workflow ? [...workflow.nodes].sort((a, b) => a.order_index - b.order_index) : [];

  async function handleToggleActive() {
    setBusy(true);
    try {
      const updated = await updateWorkflow(id, { is_active: !workflow.is_active });
      setWorkflow(updated);
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteWorkflow() {
    await deleteWorkflow(id);
    navigate("/workflows");
  }

  async function handleAddNode(nodeType, config) {
    setBusy(true);
    setError("");
    try {
      const nextOrder = sortedNodes.length;
      await addNode(id, { node_type: nodeType, order_index: nextOrder, config });
      setFormMode(null);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not add node");
    } finally {
      setBusy(false);
    }
  }

  async function handleEditNode(nodeId, nodeType, config) {
    setBusy(true);
    setError("");
    try {
      await updateNode(id, nodeId, { config });
      setFormMode(null);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not update node");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteNode(nodeId) {
    setBusy(true);
    try {
      await deleteNode(id, nodeId);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleMove(index, direction) {
    const target = sortedNodes[index + direction];
    const current = sortedNodes[index];
    if (!target) return;
    setBusy(true);
    try {
      await Promise.all([
        updateNode(id, current.id, { order_index: target.order_index }),
        updateNode(id, target.id, { order_index: current.order_index }),
      ]);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleRun(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setRunResult(null);
    try {
      const execution = await runWorkflow(id, Number(leadId));
      setRunResult(execution);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not run workflow");
    } finally {
      setBusy(false);
    }
  }

  if (!workflow) return <PageLoading label="Loading workflow..." />;

  const editingNode = typeof formMode === "number" ? sortedNodes.find((n) => n.id === formMode) : null;

  return (
    <div>
      <Link to="/workflows" className="back-link"><IconArrowLeft width={16} height={16} /> Back to workflows</Link>
      <div className="page-header">
        <h1>{workflow.name}</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" disabled={busy} onClick={handleToggleActive}>
            {workflow.is_active ? "Deactivate" : "Activate"}
          </button>
          <button className="btn btn-secondary" disabled={busy} onClick={handleDeleteWorkflow}>
            Delete workflow
          </button>
        </div>
      </div>
      <p className="muted">
        Trigger: <strong>{workflow.trigger_type}</strong> &middot; {workflow.is_active ? "Active" : "Inactive"}
      </p>
      {error && <p className="form-error">{error}</p>}

      <div className="dashboard-columns">
        <section className="panel">
          <h2>Pipeline</h2>
          <div className="node-pipeline">
            {sortedNodes.map((node, index) => (
              <div key={node.id}>
                <NodeCard
                  node={node}
                  isFirst={index === 0}
                  isLast={index === sortedNodes.length - 1}
                  onEdit={() => setFormMode(node.id)}
                  onDelete={() => handleDeleteNode(node.id)}
                  onMoveUp={() => handleMove(index, -1)}
                  onMoveDown={() => handleMove(index, 1)}
                />
                {index < sortedNodes.length - 1 && <div className="node-connector" />}
              </div>
            ))}
          </div>
          {sortedNodes.length === 0 && <p className="empty-state">No nodes yet — add one below.</p>}

          {formMode === "add" && (
            <NodeForm submitLabel="Add node" onSubmit={handleAddNode} onCancel={() => setFormMode(null)} />
          )}
          {editingNode && (
            <NodeForm
              node={editingNode}
              submitLabel="Save node"
              onSubmit={(nodeType, config) => handleEditNode(editingNode.id, nodeType, config)}
              onCancel={() => setFormMode(null)}
            />
          )}
          {formMode === null && (
            <button className="btn btn-primary" onClick={() => setFormMode("add")}>
              + Add node
            </button>
          )}
        </section>

        <section className="panel">
          <h2>Run this workflow</h2>
          <form onSubmit={handleRun}>
            <label>
              Lead ID
              <input value={leadId} onChange={(e) => setLeadId(e.target.value)} required placeholder="e.g. 3" />
            </label>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              Run
            </button>
          </form>

          {runResult && (
            <div className="test-result">
              <p>
                Status: <span className={`badge badge-${runResult.status === "success" ? "normal" : "high"}`}>{runResult.status}</span>
              </p>
              <ul className="simple-list">
                {runResult.log.steps.map((step, i) => (
                  <li key={i}>
                    <span className="node-type-badge-sm">{step.node_type}</span>
                    <span>{step.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <h2 className="mt-section">Execution history</h2>
          {executions.length === 0 && <p className="empty-state">No runs yet.</p>}
          <ul className="simple-list">
            {executions.map((ex) => (
              <li key={ex.id}>
                <span className={`badge badge-${ex.status === "success" ? "normal" : "high"}`}>{ex.status}</span>
                <span className="muted">lead #{ex.lead_id}</span>
                <span className="muted">{new Date(ex.started_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
