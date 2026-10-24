"""Audit logging and idempotency verification for mutating tools."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from src.db.models import AuditLog

def compute_idempotency_hash(tool_name: str, payload: Dict[str, Any]) -> str:
    """Generate deterministic SHA256 idempotency key for an operation."""
    raw = f"{tool_name}:{json.dumps(payload, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()

def record_audit(
    db: Session,
    agent_name: str,
    tool_name: str,
    action_type: str,
    payload: Dict[str, Any],
    success: bool = True,
    event_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
) -> AuditLog:
    """Persist an audit entry in the database."""
    idem_key = idempotency_key or compute_idempotency_hash(tool_name, payload)
    log_entry = AuditLog(
        event_id=event_id,
        agent_name=agent_name,
        tool_name=tool_name,
        action_type=action_type,
        payload_summary=json.dumps(payload, default=str)[:1000],
        success=success,
        idempotency_key=idem_key,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
