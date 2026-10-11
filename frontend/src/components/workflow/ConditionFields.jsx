import { FIELD_OPTIONS, OPERATOR_OPTIONS } from "./nodeMeta";

function coerceValue(field, raw) {
  if (raw.trim().toLowerCase() === "null") return null;
  if (field === "score" || field === "confidence") {
    const num = Number(raw);
    return Number.isNaN(num) ? raw : num;
  }
  return raw;
}

function ClauseRow({ clause, onChange, onRemove, showRemove }) {
  return (
    <div className="clause-row">
      <select value={clause.field} onChange={(e) => onChange({ ...clause, field: e.target.value })}>
        {FIELD_OPTIONS.map((f) => (
          <option key={f.value} value={f.value}>
            {f.label}
          </option>
        ))}
      </select>
      <select value={clause.operator} onChange={(e) => onChange({ ...clause, operator: e.target.value })}>
        {OPERATOR_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <input
        value={clause.rawValue}
        onChange={(e) => onChange({ ...clause, rawValue: e.target.value })}
        placeholder="value (e.g. 80, complaint, null)"
      />
      {showRemove && (
        <button type="button" className="btn btn-sm btn-secondary" onClick={onRemove}>
          Remove
        </button>
      )}
    </div>
  );
}

export function emptyClause() {
  return { field: "score", operator: "gt", rawValue: "" };
}

export function clausesFromConfig(config) {
  if (config?.clauses) {
    return {
      logic: config.logic || "all",
      clauses: config.clauses.map((c) => ({ field: c.field, operator: c.operator, rawValue: String(c.value ?? "") })),
    };
  }
  if (config?.field) {
    return { logic: "single", clauses: [{ field: config.field, operator: config.operator, rawValue: String(config.value ?? "") }] };
  }
  return { logic: "single", clauses: [emptyClause()] };
}

export function clausesToConfig(logic, clauses) {
  const built = clauses.map((c) => ({ field: c.field, operator: c.operator, value: coerceValue(c.field, c.rawValue) }));
  if (logic === "single") {
    return built[0];
  }
  return { logic, clauses: built };
}

export default function ConditionFields({ logic, clauses, onChange }) {
  function updateClause(index, updated) {
    const next = [...clauses];
    next[index] = updated;
    onChange(logic, next);
  }

  function addClause() {
    onChange("all", [...clauses, emptyClause()]);
  }

  function removeClause(index) {
    onChange(logic, clauses.filter((_, i) => i !== index));
  }

  return (
    <div>
      <label>
        Match
        <select value={logic} onChange={(e) => onChange(e.target.value, clauses)}>
          <option value="single">a single condition</option>
          <option value="all">ALL of these conditions (AND)</option>
          <option value="any">ANY of these conditions (OR)</option>
        </select>
      </label>
      {clauses.map((clause, i) => (
        <ClauseRow
          key={i}
          clause={clause}
          onChange={(updated) => updateClause(i, updated)}
          onRemove={() => removeClause(i)}
          showRemove={logic !== "single" && clauses.length > 1}
        />
      ))}
      {logic !== "single" && (
        <button type="button" className="btn btn-sm btn-secondary" onClick={addClause}>
          + Add condition
        </button>
      )}
    </div>
  );
}
