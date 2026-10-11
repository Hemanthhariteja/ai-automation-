import { describeNode, nodeColor, nodeLabel } from "./nodeMeta";

export default function NodeCard({ node, isFirst, isLast, onEdit, onDelete, onMoveUp, onMoveDown }) {
  return (
    <div className="node-card" style={{ borderLeftColor: nodeColor(node.node_type) }}>
      <div className="node-card-header">
        <span className="node-type-badge" style={{ background: nodeColor(node.node_type) }}>
          {nodeLabel(node.node_type)}
        </span>
        <div className="node-card-actions">
          <button className="btn btn-sm btn-secondary" disabled={isFirst} onClick={onMoveUp} title="Move up">
            ↑
          </button>
          <button className="btn btn-sm btn-secondary" disabled={isLast} onClick={onMoveDown} title="Move down">
            ↓
          </button>
          <button className="btn btn-sm btn-secondary" onClick={onEdit}>
            Edit
          </button>
          <button className="btn btn-sm btn-secondary" onClick={onDelete}>
            Delete
          </button>
        </div>
      </div>
      <p className="node-card-summary">{describeNode(node)}</p>
    </div>
  );
}
