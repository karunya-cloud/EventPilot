"""EventPilot AI Tools Package."""
from src.tools.audit import record_audit, compute_idempotency_hash
from src.tools.event_tools import (
    create_event,
    get_event,
    get_dashboard_summary,
    retrieve_historical_event_metrics,
)
from src.tools.task_tools import (
    generate_timeline,
    create_task,
    update_task,
    list_overdue_tasks,
)
from src.tools.registration_tools import (
    register_participant,
    cancel_registration,
    promote_waitlisted_participant,
)
from src.tools.attendance_tools import (
    generate_checkin_qr_png_base64,
    check_in_attendee,
    generate_attendance_report,
)
from src.tools.logistics_tools import (
    check_resource_shortages,
    update_inventory,
    record_expense,
    calculate_budget,
)
from src.tools.risk_tools import (
    detect_risks,
    generate_mitigation_options,
    apply_approved_mitigation,
)
from src.tools.communication_tools import (
    draft_email,
    request_email_approval,
    send_approved_email,
)
