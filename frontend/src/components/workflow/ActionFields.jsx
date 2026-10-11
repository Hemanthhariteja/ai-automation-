import { ACTION_TYPE_OPTIONS } from "./nodeMeta";

export default function ActionFields({ config, onChange }) {
  function set(field, value) {
    onChange({ ...config, [field]: value });
  }

  return (
    <div>
      <label>
        Action type
        <select value={config.action_type || ""} onChange={(e) => onChange({ action_type: e.target.value })}>
          <option value="" disabled>
            Choose an action...
          </option>
          {ACTION_TYPE_OPTIONS.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
            </option>
          ))}
        </select>
      </label>

      {config.action_type === "update_lead_status" && (
        <label>
          New status
          <select value={config.value || "new"} onChange={(e) => set("value", e.target.value)}>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="won">Won</option>
            <option value="lost">Lost</option>
          </select>
        </label>
      )}

      {config.action_type === "set_priority" && (
        <label>
          New priority
          <select value={config.value || "normal"} onChange={(e) => set("value", e.target.value)}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
        </label>
      )}

      {config.action_type === "create_notification" && (
        <>
          <label>
            Message
            <input value={config.message || ""} onChange={(e) => set("message", e.target.value)} />
          </label>
          <label>
            Notification type
            <input
              value={config.notification_type || "info"}
              onChange={(e) => set("notification_type", e.target.value)}
              placeholder="info, high_priority_lead, ..."
            />
          </label>
        </>
      )}

      {config.action_type === "add_task" && (
        <>
          <label>
            Task title
            <input value={config.title || ""} onChange={(e) => set("title", e.target.value)} />
          </label>
          <label>
            Description (optional)
            <input value={config.description || ""} onChange={(e) => set("description", e.target.value)} />
          </label>
        </>
      )}

      {config.action_type === "send_email" && (
        <>
          <label>
            Recipient (optional — defaults to the lead&apos;s customer email)
            <input value={config.recipient || ""} onChange={(e) => set("recipient", e.target.value)} />
          </label>
          <label>
            Subject
            <input value={config.subject || ""} onChange={(e) => set("subject", e.target.value)} />
          </label>
        </>
      )}

      {config.action_type === "send_messenger_reply" && (
        <label>
          Reply message
          <input
            value={config.message || ""}
            onChange={(e) => set("message", e.target.value)}
            placeholder="Thanks for your message — we'll get back to you shortly."
          />
        </label>
      )}

      {config.action_type === "log_execution" && (
        <label>
          Log message
          <input value={config.message || ""} onChange={(e) => set("message", e.target.value)} />
        </label>
      )}
    </div>
  );
}
