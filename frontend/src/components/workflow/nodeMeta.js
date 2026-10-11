export const NODE_TYPES = [
  { value: "trigger", label: "Trigger", color: "#2563eb" },
  { value: "ai_processor", label: "AI Processor", color: "#7c3aed" },
  { value: "condition", label: "Condition", color: "#b7791f" },
  { value: "action", label: "Action", color: "#1a8a5f" },
  { value: "notification", label: "Notification", color: "#0e7490" },
  { value: "db", label: "DB", color: "#4b5563" },
  { value: "end", label: "End", color: "#111827" },
];

export const FIELD_OPTIONS = [
  { value: "score", label: "Score" },
  { value: "intent", label: "Intent" },
  { value: "category", label: "Category" },
  { value: "confidence", label: "Confidence" },
  { value: "priority", label: "Priority" },
  { value: "status", label: "Status" },
  { value: "extracted_data.urgency", label: "Extracted: Urgency" },
  { value: "extracted_data.budget", label: "Extracted: Budget" },
  { value: "extracted_data.product_or_service", label: "Extracted: Product/Service" },
];

export const OPERATOR_OPTIONS = [
  { value: "eq", label: "equals" },
  { value: "neq", label: "not equals" },
  { value: "gt", label: "greater than" },
  { value: "gte", label: "greater than or equal" },
  { value: "lt", label: "less than" },
  { value: "lte", label: "less than or equal" },
  { value: "contains", label: "contains" },
];

export const ACTION_TYPE_OPTIONS = [
  { value: "update_lead_status", label: "Update lead status" },
  { value: "set_priority", label: "Set priority" },
  { value: "save_lead", label: "Save lead (no-op, already persisted)" },
  { value: "create_notification", label: "Create notification" },
  { value: "add_task", label: "Add task" },
  { value: "generate_ai_response", label: "Generate AI response" },
  { value: "generate_summary", label: "Generate summary" },
  { value: "send_email", label: "Send email (simulated)" },
  { value: "send_messenger_reply", label: "Reply on Messenger (simulated)" },
  { value: "log_execution", label: "Log message" },
];

export function nodeColor(nodeType) {
  return NODE_TYPES.find((n) => n.value === nodeType)?.color || "#888";
}

export function nodeLabel(nodeType) {
  return NODE_TYPES.find((n) => n.value === nodeType)?.label || nodeType;
}

function clauseSummary(clause) {
  const op = OPERATOR_OPTIONS.find((o) => o.value === clause.operator)?.label || clause.operator;
  return `${clause.field} ${op} ${JSON.stringify(clause.value)}`;
}

export function describeNode(node) {
  const config = node.config || {};

  switch (node.node_type) {
    case "trigger":
      return "Starts the workflow";
    case "ai_processor":
      return config.force ? "Re-run AI classification (forced)" : "Classify lead if not already classified";
    case "condition":
      if (config.clauses) {
        return `IF (${config.clauses.map(clauseSummary).join(config.logic === "any" ? " OR " : " AND ")})`;
      }
      return `IF ${clauseSummary(config)}`;
    case "action":
    case "db":
      return describeAction(config);
    case "notification":
      return `NOTIFY: "${config.message || "(no message)"}"`;
    case "end":
      return "Ends the workflow";
    default:
      return JSON.stringify(config);
  }
}

function describeAction(config) {
  switch (config.action_type) {
    case "update_lead_status":
      return `SET status = ${config.value}`;
    case "set_priority":
      return `SET priority = ${config.value}`;
    case "save_lead":
      return "Save lead (no-op)";
    case "create_notification":
      return `NOTIFY: "${config.message || "(no message)"}"`;
    case "add_task":
      return `ADD TASK: "${config.title || "(untitled)"}"`;
    case "generate_ai_response":
      return "Generate AI response";
    case "generate_summary":
      return "Generate conversation summary";
    case "send_email":
      return `SEND EMAIL (simulated) to ${config.recipient || "customer"}: "${config.subject || ""}"`;
    case "send_messenger_reply":
      return `REPLY ON MESSENGER (simulated): "${config.message || ""}"`;
    case "log_execution":
      return `LOG: "${config.message || ""}"`;
    default:
      return config.action_type ? `Unknown action: ${config.action_type}` : "No action configured";
  }
}
