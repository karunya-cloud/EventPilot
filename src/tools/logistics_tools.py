"""Logistics, inventory reserves, and budget ledger tools."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.db.models import (
    InventoryItem,
    EquipmentAllocation,
    Expense,
    ExpenseStatus,
    Event,
)
from src.tools.audit import record_audit, compute_idempotency_hash

def check_resource_shortages(
    db: Session,
    event_id: int,
    item_name: str,
    required_quantity: int,
    agent_name: str = "LogisticsAgent",
) -> Dict[str, Any]:
    """Check inventory stock against required event capacity and calculate exact deficits."""
    item = db.query(InventoryItem).filter(InventoryItem.name == item_name).first()
    if not item:
        raise ValueError(f"Inventory item '{item_name}' does not exist in inventory depot.")

    available = item.available_quantity
    shortage = max(0, required_quantity - available)
    is_sufficient = shortage == 0

    return {
        "event_id": event_id,
        "item_name": item.name,
        "required_quantity": required_quantity,
        "available_quantity": available,
        "shortage": shortage,
        "is_sufficient": is_sufficient,
        "unit_cost": item.unit_cost,
        "location": item.location,
    }

def update_inventory(
    db: Session,
    item_name: str,
    available_delta: int,
    agent_name: str = "LogisticsAgent",
) -> Dict[str, Any]:
    """Atomically adjust available quantity for an inventory item."""
    item = db.query(InventoryItem).filter(InventoryItem.name == item_name).first()
    if not item:
        raise ValueError(f"Inventory item '{item_name}' not found.")

    new_qty = item.available_quantity + available_delta
    if new_qty < 0:
        raise ValueError(f"Insufficient stock for '{item_name}'. Current: {item.available_quantity}, requested: {available_delta}")

    item.available_quantity = new_qty
    db.commit()
    db.refresh(item)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="update_inventory",
        action_type="UPDATE_INVENTORY",
        payload={"item_name": item_name, "delta": available_delta, "new_available": new_qty},
        success=True,
    )

    return {
        "item_name": item.name,
        "available_quantity": item.available_quantity,
        "total_quantity": item.total_quantity,
    }

def record_expense(
    db: Session,
    event_id: int,
    category: str,
    description: str,
    amount: float,
    approved_by: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    agent_name: str = "LogisticsAgent",
) -> Dict[str, Any]:
    """Record an event expense with idempotency protection."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    key = idempotency_key or compute_idempotency_hash(
        "record_expense",
        {"event_id": event_id, "category": category, "desc": description, "amount": amount},
    )

    existing = db.query(Expense).filter(Expense.idempotency_key == key).first()
    if existing:
        return {
            "expense_id": existing.id,
            "status": existing.status.value,
            "amount": existing.amount,
            "is_duplicate_suppressed": True,
        }

    expense = Expense(
        event_id=event_id,
        category=category,
        description=description,
        amount=amount,
        status=ExpenseStatus.APPROVED if approved_by else ExpenseStatus.PENDING,
        approved_by=approved_by,
        idempotency_key=key,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="record_expense",
        action_type="INSERT_EXPENSE",
        payload={"expense_id": expense.id, "amount": amount, "category": category},
        success=True,
        event_id=event_id,
        idempotency_key=key,
    )

    return {
        "expense_id": expense.id,
        "amount": expense.amount,
        "status": expense.status.value,
        "category": expense.category,
        "is_duplicate_suppressed": False,
    }

def calculate_budget(db: Session, event_id: int) -> Dict[str, Any]:
    """Calculate allocated budget, total committed expenses, and remaining runway."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    expenses = db.query(Expense).filter(Expense.event_id == event_id).all()
    
    total_approved = sum(e.amount for e in expenses if e.status in [ExpenseStatus.APPROVED, ExpenseStatus.PAID])
    total_pending = sum(e.amount for e in expenses if e.status == ExpenseStatus.PENDING)
    total_committed = total_approved + total_pending
    remaining = event.budget - total_committed

    return {
        "event_id": event.id,
        "total_budget": event.budget,
        "currency": event.currency,
        "approved_expenses": total_approved,
        "pending_expenses": total_pending,
        "total_committed": total_committed,
        "remaining_budget": remaining,
        "is_over_budget": remaining < 0,
    }
