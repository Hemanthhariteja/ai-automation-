"""Ready-made rule definitions matching the CLAUDE.md examples literally.
Instantiating one creates a normal, editable Workflow + WorkflowNode rows —
these are just starting points, not a separate mechanism. Adding a new
template here is additive: nothing else in the engine needs to change."""

WORKFLOW_TEMPLATES = {
    "high_score_alert": {
        "name": "High-score lead alert",
        "description": "Notifies you and marks a lead high-priority when the AI score is above 80.",
        "trigger_type": "new_enquiry",
        "nodes": [
            {"node_type": "trigger", "order_index": 0, "config": None},
            {"node_type": "condition", "order_index": 1, "config": {"field": "score", "operator": "gt", "value": 80}},
            {
                "node_type": "notification",
                "order_index": 2,
                "config": {
                    "message": "A high-scoring lead just came in — take a look.",
                    "notification_type": "high_priority_lead",
                },
            },
            {"node_type": "action", "order_index": 3, "config": {"action_type": "set_priority", "value": "high"}},
            {"node_type": "end", "order_index": 4, "config": None},
        ],
    },
    "complaint_priority": {
        "name": "Escalate complaints",
        "description": "Marks a lead high-priority whenever the AI classifies it as a complaint.",
        "trigger_type": "new_enquiry",
        "nodes": [
            {"node_type": "trigger", "order_index": 0, "config": None},
            {
                "node_type": "condition",
                "order_index": 1,
                "config": {"field": "intent", "operator": "eq", "value": "complaint"},
            },
            {"node_type": "action", "order_index": 2, "config": {"action_type": "set_priority", "value": "high"}},
            {
                "node_type": "notification",
                "order_index": 3,
                "config": {"message": "A complaint just came in — may need urgent attention.", "notification_type": "info"},
            },
            {"node_type": "end", "order_index": 4, "config": None},
        ],
    },
    "auto_respond_and_followup": {
        "name": "Auto-respond and schedule follow-up",
        "description": "Drafts an AI reply and adds a follow-up task for every new enquiry.",
        "trigger_type": "new_enquiry",
        "nodes": [
            {"node_type": "trigger", "order_index": 0, "config": None},
            {"node_type": "action", "order_index": 1, "config": {"action_type": "generate_ai_response"}},
            {
                "node_type": "action",
                "order_index": 2,
                "config": {"action_type": "add_task", "title": "Follow up on new enquiry"},
            },
            {"node_type": "end", "order_index": 3, "config": None},
        ],
    },
    "urgent_and_high_budget": {
        "name": "Urgent + high budget alert",
        "description": "Compound rule: notifies you only when a lead is BOTH urgent AND mentions a budget.",
        "trigger_type": "new_enquiry",
        "nodes": [
            {"node_type": "trigger", "order_index": 0, "config": None},
            {
                "node_type": "condition",
                "order_index": 1,
                "config": {
                    "logic": "all",
                    "clauses": [
                        {"field": "extracted_data.urgency", "operator": "eq", "value": "high"},
                        {"field": "extracted_data.budget", "operator": "neq", "value": None},
                    ],
                },
            },
            {
                "node_type": "notification",
                "order_index": 2,
                "config": {"message": "Urgent lead with a stated budget — worth a fast follow-up.", "notification_type": "high_priority_lead"},
            },
            {"node_type": "end", "order_index": 3, "config": None},
        ],
    },
}
