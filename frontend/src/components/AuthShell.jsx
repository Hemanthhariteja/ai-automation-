import { IconAI, IconAnalytics, IconWorkflow } from "./Icons";

const HIGHLIGHTS = [
  { Icon: IconAI, text: "AI classifies, scores, and drafts replies to every enquiry automatically" },
  { Icon: IconWorkflow, text: "A rule-based workflow engine reacts to leads the moment they arrive" },
  { Icon: IconAnalytics, text: "Live dashboard and analytics — no spreadsheets, no lost enquiries" },
];

export default function AuthShell({ children }) {
  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-panel-brand">
          <span className="brand-mark">TF</span>
          <span className="auth-panel-name">TechFix Automation</span>
        </div>
        <h1 className="auth-panel-headline">Run your business's front door on autopilot.</h1>
        <p className="auth-panel-sub">
          A small CRM that classifies, scores, and responds to customer enquiries automatically —
          built to run entirely free, with no AI provider required to get started.
        </p>
        <ul className="auth-highlight-list">
          {HIGHLIGHTS.map(({ Icon, text }) => (
            <li key={text}>
              <span className="auth-highlight-icon"><Icon width={16} height={16} /></span>
              <span>{text}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="auth-form-side">{children}</div>
    </div>
  );
}
