import { useState } from "react";
import { NODE_TYPES } from "./nodeMeta";
import ConditionFields, { clausesFromConfig, clausesToConfig } from "./ConditionFields";
import ActionFields from "./ActionFields";

function buildConfig(nodeType, state) {
  switch (nodeType) {
    case "condition":
      return clausesToConfig(state.condition.logic, state.condition.clauses);
    case "action":
    case "db":
      return state.action;
    case "notification":
      return { message: state.notification.message, notification_type: state.notification.notificationType || "info" };
    case "ai_processor":
      return { force: state.aiProcessor.force };
    default:
      return null;
  }
}

function initialState(node) {
  const config = node?.config || {};
  return {
    condition: clausesFromConfig(config),
    action: node?.node_type === "action" || node?.node_type === "db" ? config : {},
    notification: {
      message: node?.node_type === "notification" ? config.message || "" : "",
      notificationType: node?.node_type === "notification" ? config.notification_type || "info" : "info",
    },
    aiProcessor: { force: node?.node_type === "ai_processor" ? Boolean(config.force) : false },
  };
}

export default function NodeForm({ node, onSubmit, onCancel, submitLabel }) {
  const [nodeType, setNodeType] = useState(node?.node_type || "condition");
  const [state, setState] = useState(initialState(node));
  const [error, setError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if ((nodeType === "action" || nodeType === "db") && !state.action.action_type) {
      setError("Choose an action type.");
      return;
    }
    setError("");
    onSubmit(nodeType, buildConfig(nodeType, state));
  }

  return (
    <form className="panel node-form" onSubmit={handleSubmit}>
      {error && <p className="form-error">{error}</p>}
      <label>
        Node type
        <select value={nodeType} onChange={(e) => setNodeType(e.target.value)} disabled={Boolean(node)}>
          {NODE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </label>

      {nodeType === "condition" && (
        <ConditionFields
          logic={state.condition.logic}
          clauses={state.condition.clauses}
          onChange={(logic, clauses) => setState((s) => ({ ...s, condition: { logic, clauses } }))}
        />
      )}

      {(nodeType === "action" || nodeType === "db") && (
        <ActionFields config={state.action} onChange={(action) => setState((s) => ({ ...s, action }))} />
      )}

      {nodeType === "notification" && (
        <>
          <label>
            Message
            <input
              value={state.notification.message}
              onChange={(e) => setState((s) => ({ ...s, notification: { ...s.notification, message: e.target.value } }))}
            />
          </label>
          <label>
            Notification type
            <input
              value={state.notification.notificationType}
              onChange={(e) =>
                setState((s) => ({ ...s, notification: { ...s.notification, notificationType: e.target.value } }))
              }
            />
          </label>
        </>
      )}

      {nodeType === "ai_processor" && (
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={state.aiProcessor.force}
            onChange={(e) => setState((s) => ({ ...s, aiProcessor: { force: e.target.checked } }))}
          />
          Force re-classification even if already classified
        </label>
      )}

      {(nodeType === "trigger" || nodeType === "end") && (
        <p className="muted">This node type has no configuration.</p>
      )}

      <div className="button-row">
        <button type="submit" className="btn btn-primary">
          {submitLabel}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
