export default function EmptyState({ Icon, text, action }) {
  return (
    <div className="empty-state">
      {Icon && <Icon width={20} height={20} className="empty-state-icon" />}
      <span>{text}</span>
      {action}
    </div>
  );
}
