from dataclasses import dataclass

from app.ai.service import AllProvidersFailedError
from app.models.business import Business
from app.models.lead import Lead
from app.models.notification import Notification
from app.models.task import Task
from app.services.lead_ai import run_ai_pipeline_on_lead
from app.services.response_service import generate_ai_response_for_lead, summarize_conversation


@dataclass
class NodeResult:
    status: str  # ok | halt | failed  — halt = condition not met, not an error
    detail: str


def _trigger_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    return NodeResult("ok", f"Triggered for lead #{lead.id}")


def _ai_processor_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    force = bool(config.get("force", False))
    if lead.intent is not None and not force:
        return NodeResult("ok", "Lead already classified — skipped re-run")
    if not lead.raw_message:
        return NodeResult("ok", "Lead has no message to classify — skipped")

    ai_ran, _ = run_ai_pipeline_on_lead(db, business, lead)
    return NodeResult("ok" if ai_ran else "failed", "Classification ran" if ai_ran else "All AI providers failed")


OPERATORS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "gte": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b,
    "lte": lambda a, b: a is not None and a <= b,
    "contains": lambda a, b: a is not None and b in a,
}


def _resolve_field(lead: Lead, field: str):
    """extracted_data.<key> reaches into the AI-extracted JSON (budget,
    urgency, etc); anything else is looked up as a plain Lead column."""
    if field.startswith("extracted_data."):
        key = field.split(".", 1)[1]
        data = lead.extracted_data or {}
        return data.get(key)
    return getattr(lead, field, None)


def _evaluate_clause(lead: Lead, clause: dict) -> tuple[bool, str]:
    field = clause.get("field")
    operator = clause.get("operator", "eq")
    value = clause.get("value")

    if field is None or operator not in OPERATORS:
        raise ValueError(f"Invalid condition clause: {clause}")

    actual = _resolve_field(lead, field)
    try:
        passed = OPERATORS[operator](actual, value)
    except TypeError as exc:
        raise ValueError(f"Condition could not be evaluated ({field}={actual!r} {operator} {value!r}): {exc}")
    return passed, f"{field} {operator} {value!r} (actual={actual!r})"


def evaluate_condition(lead: Lead, config: dict) -> tuple[bool, str]:
    """Pure evaluation — no side effects — reused by both the workflow
    engine and the standalone condition-preview endpoint. Two shapes:
    simple {"field", "operator", "value"} (Phase 8, unchanged), or compound
    {"logic": "all"|"any", "clauses": [...]} for AND/OR of multiple simple
    clauses. Raises ValueError on a malformed config; never raises for a
    condition that's merely false."""
    clauses = config.get("clauses")
    if clauses is not None:
        logic = config.get("logic", "all")
        if logic not in ("all", "any") or not isinstance(clauses, list) or not clauses:
            raise ValueError(f"Invalid compound condition config: {config}")
        results = [_evaluate_clause(lead, c) for c in clauses]
        passed = all(r[0] for r in results) if logic == "all" else any(r[0] for r in results)
        detail = f"[{logic}] " + " | ".join(r[1] for r in results)
        return passed, detail

    return _evaluate_clause(lead, config)


def _condition_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    try:
        passed, detail = evaluate_condition(lead, config)
    except ValueError as exc:
        return NodeResult("failed", str(exc))

    if passed:
        return NodeResult("ok", f"Condition met: {detail}")
    return NodeResult("halt", f"Condition not met: {detail} — stopping here")


def _action_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    action_type = config.get("action_type")

    if action_type == "update_lead_status":
        lead.status = config.get("value", lead.status)
        return NodeResult("ok", f"Lead status set to '{lead.status}'")

    if action_type == "set_priority":
        lead.priority = config.get("value", lead.priority)
        return NodeResult("ok", f"Lead priority set to '{lead.priority}'")

    if action_type == "save_lead":
        db.flush()
        return NodeResult("ok", "Lead persisted")

    if action_type == "create_notification":
        message = config.get("message") or f"Update on lead #{lead.id}"
        notification = Notification(
            business_id=business.id, type=config.get("notification_type", "info"), message=message
        )
        db.add(notification)
        db.flush()
        return NodeResult("ok", f"Notification created: {message}")

    if action_type == "add_task":
        title = config.get("title") or f"Follow up with lead #{lead.id}"
        task = Task(business_id=business.id, lead_id=lead.id, title=title, description=config.get("description"))
        db.add(task)
        db.flush()
        return NodeResult("ok", f"Task created: {title}")

    if action_type == "generate_ai_response":
        if not lead.raw_message:
            return NodeResult("ok", "Lead has no message — skipped response generation")
        try:
            _, _, provider_used, fallback_used, _ = generate_ai_response_for_lead(db, business, lead)
        except AllProvidersFailedError as exc:
            return NodeResult("failed", f"Response generation failed: {exc}")
        return NodeResult("ok", f"AI response generated via {provider_used} (fallback={fallback_used})")

    if action_type == "generate_summary":
        try:
            summarize_conversation(db, business, lead)
        except AllProvidersFailedError as exc:
            return NodeResult("failed", f"Summarization failed: {exc}")
        return NodeResult("ok", "Conversation summarized")

    if action_type == "send_email":
        recipient = config.get("recipient") or (lead.customer.email if lead.customer else None) or "unknown recipient"
        subject = config.get("subject", "Update on your enquiry")
        detail = f'[SIMULATED] Email would be sent to {recipient}: "{subject}" (no email provider configured)'
        notification = Notification(business_id=business.id, type="email_simulation", message=detail)
        db.add(notification)
        db.flush()
        return NodeResult("ok", detail)

    if action_type == "send_messenger_reply":
        # Always simulated — actually sending requires the Send API and a
        # real Page access token, out of scope for this pass (the channel
        # ships with real *receiving*; replying is documented future work,
        # not silently pretended to work).
        tracking = lead.tracking_data or {}
        recipient = tracking.get("sender_external_id", "unknown sender")
        message = config.get("message", "Thanks for your message — we'll get back to you shortly.")
        detail = f'[SIMULATED] Messenger reply would be sent to {recipient}: "{message}" (sending not wired up yet)'
        notification = Notification(business_id=business.id, type="messenger_simulation", message=detail)
        db.add(notification)
        db.flush()
        return NodeResult("ok", detail)

    if action_type == "log_execution":
        return NodeResult("ok", config.get("message", "Execution logged"))

    return NodeResult("failed", f"Unknown action_type: {action_type!r}")


def _notification_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    return _action_handler(db, business, lead, {**config, "action_type": "create_notification"})


def _db_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    # "DB" nodes in the visual builder are actions that persist state — same
    # dispatcher as "action" nodes rather than duplicating the logic.
    return _action_handler(db, business, lead, config)


def _end_handler(db, business: Business, lead: Lead, config: dict) -> NodeResult:
    return NodeResult("ok", "Workflow complete")


NODE_HANDLERS = {
    "trigger": _trigger_handler,
    "ai_processor": _ai_processor_handler,
    "condition": _condition_handler,
    "action": _action_handler,
    "notification": _notification_handler,
    "db": _db_handler,
    "end": _end_handler,
}
