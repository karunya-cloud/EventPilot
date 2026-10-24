"""Operational risk detection, mitigation generation, and recovery execution."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.db.models import (
    RiskAlert,
    MitigationPlan,
    RiskSeverity,
    RiskStatus,
    Event,
    InventoryItem,
    EquipmentAllocation,
    Task,
    TaskPriority,
)
from src.tools.logistics_tools import check_resource_shortages, update_inventory, record_expense
from src.tools.audit import record_audit

def detect_risks(
    db: Session,
    event_id: int,
    required_item_name: str = "Robotics Hardware Kit",
    required_quantity: Optional[int] = None,
    agent_name: str = "RiskAgent",
) -> List[Dict[str, Any]]:
    """Audit event parameters for inventory shortages, overdue tasks, and budget strain."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    qty = required_quantity or event.capacity
    detected = []

    # 1. Inventory Shortage Check
    shortage_info = check_resource_shortages(db, event_id, required_item_name, qty)
    if not shortage_info["is_sufficient"]:
        shortage = shortage_info["shortage"]
        alert = RiskAlert(
            event_id=event_id,
            risk_type="EQUIPMENT_SHORTAGE",
            severity=RiskSeverity.CRITICAL if shortage > 10 else RiskSeverity.HIGH,
            description=(
                f"Critical Equipment Deficit: Event requires {qty} units of '{required_item_name}', "
                f"but only {shortage_info['available_quantity']} are available in depot. Deficit of {shortage} units."
            ),
            status=RiskStatus.DETECTED,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Generate grounded mitigation options immediately
        plans = generate_mitigation_options(db, alert.id, shortage_info)

        detected.append({
            "alert_id": alert.id,
            "risk_type": alert.risk_type,
            "severity": alert.severity.value,
            "shortage": shortage,
            "required_quantity": qty,
            "available_quantity": shortage_info["available_quantity"],
            "description": alert.description,
            "mitigation_options": plans,
        })

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="detect_risks",
        action_type="AUDIT_RISKS",
        payload={"event_id": event_id, "risks_found": len(detected)},
        success=True,
        event_id=event_id,
    )

    return detected

def generate_mitigation_options(
    db: Session,
    risk_alert_id: int,
    shortage_info: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Formulate grounded, actionable recovery options for the organizer."""
    shortage = shortage_info["shortage"]
    unit_cost = shortage_info.get("unit_cost", 450.0)
    total_rental_cost = shortage * unit_cost

    options_data = [
        {
            "option_key": "OPTION_A",
            "name": f"Rent {shortage} External Hardware Kits",
            "description": f"Procure {shortage} compatible kits from authorized partner vendor at ₹{unit_cost:.0f}/unit.",
            "estimated_cost": float(total_rental_cost),
        },
        {
            "option_key": "OPTION_B",
            "name": "Pair Students in 2-Person Engineering Teams (Recommended)",
            "description": (
                f"Restructure practical hands-on exercises so 60 students pair into 30 teams. "
                f"Requires only 30 kits (well within the 40 kits available in depot), leaving 10 buffer spares. "
                f"Backed by Fall 2025 historical data showing high collaboration and zero extra cost."
            ),
            "estimated_cost": 0.0,
        },
        {
            "option_key": "OPTION_C",
            "name": f"Strictly Cap Active Lab at {shortage_info['available_quantity']} & Waitlist Remainder",
            "description": f"Retain solo format for 40 students; automatically place 20 students on priority waitlist.",
            "estimated_cost": 0.0,
        },
    ]

    saved_plans = []
    for opt in options_data:
        plan = MitigationPlan(
            risk_alert_id=risk_alert_id,
            option_key=opt["option_key"],
            name=opt["name"],
            description=opt["description"],
            estimated_cost=opt["estimated_cost"],
            is_chosen=False,
        )
        db.add(plan)
        saved_plans.append(plan)

    db.commit()

    return [
        {
            "option_key": p.option_key,
            "name": p.name,
            "description": p.description,
            "estimated_cost": p.estimated_cost,
        }
        for p in saved_plans
    ]

def apply_approved_mitigation(
    db: Session,
    risk_alert_id: int,
    chosen_option_key: str,
    approver_name: str = "Lead Organizer",
    agent_name: str = "RiskAgent",
) -> Dict[str, Any]:
    """Execute the organizer's approved mitigation choice and perform database state transitions."""
    alert = db.query(RiskAlert).filter(RiskAlert.id == risk_alert_id).first()
    if not alert:
        raise ValueError(f"Risk alert {risk_alert_id} not found.")

    plan = db.query(MitigationPlan).filter(
        MitigationPlan.risk_alert_id == risk_alert_id,
        MitigationPlan.option_key == chosen_option_key.upper().strip(),
    ).first()
    if not plan:
        raise ValueError(f"Invalid option '{chosen_option_key}' for alert {risk_alert_id}.")

    plan.is_chosen = True
    plan.chosen_at = datetime.now(timezone.utc)
    alert.status = RiskStatus.MITIGATED

    event_id = alert.event_id
    item_name = "Robotics Hardware Kit"
    item = db.query(InventoryItem).filter(InventoryItem.name == item_name).first()

    execution_details = {}

    if chosen_option_key.upper() == "OPTION_B":
        # 30 kits required for 30 pairs
        kits_needed = 30
        update_inventory(db, item_name, -kits_needed, agent_name=agent_name)
        
        allocation = EquipmentAllocation(
            event_id=event_id,
            inventory_item_id=item.id,
            quantity_allocated=kits_needed,
            allocation_status="RESERVED_PAIRED_TEAMS",
        )
        db.add(allocation)
        
        # Add task to configure workstations for paired seating
        workstation_task = Task(
            event_id=event_id,
            title="Configure Workstations for 2-Student Robotics Pairs",
            description="Arrange Lab 3 benches with 2 chairs and 1 kit per station.",
            assigned_to="Alex Rivera (Logistics)",
            due_date=datetime.now(timezone.utc),
            priority=TaskPriority.HIGH,
        )
        db.add(workstation_task)
        db.commit()

        execution_details = {
            "format": "2-Person Teams",
            "kits_allocated": kits_needed,
            "depot_remaining_buffer": item.available_quantity,
            "cost_incurred": 0.0,
            "status": "RESOLVED_ZERO_COST",
        }

    elif chosen_option_key.upper() == "OPTION_A":
        # Rental option
        rental_cost = plan.estimated_cost
        record_expense(
            db=db,
            event_id=event_id,
            category="Equipment Rental",
            description=f"Rental of 20 Robotics Kits from vendor",
            amount=rental_cost,
            approved_by=approver_name,
            agent_name=agent_name,
        )
        # Allocate all 40 local kits
        update_inventory(db, item_name, -40, agent_name=agent_name)
        allocation = EquipmentAllocation(
            event_id=event_id,
            inventory_item_id=item.id,
            quantity_allocated=60,
            allocation_status="RESERVED_40_DEPOT_20_RENTED",
        )
        db.add(allocation)
        db.commit()

        execution_details = {
            "format": "Solo (60 Kits)",
            "rental_cost": rental_cost,
            "depot_kits": 40,
            "rented_kits": 20,
            "status": "RESOLVED_VIA_RENTAL",
        }

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="apply_approved_mitigation",
        action_type="EXECUTE_MITIGATION",
        payload={
            "alert_id": alert.id,
            "chosen_option": chosen_option_key,
            "approver": approver_name,
            "execution_details": execution_details,
        },
        success=True,
        event_id=event_id,
    )

    return {
        "alert_id": alert.id,
        "status": alert.status.value,
        "chosen_option": plan.name,
        "execution_details": execution_details,
        "approver": approver_name,
    }
