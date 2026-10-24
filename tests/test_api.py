"""Integration tests for FastAPI REST Endpoints."""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from src.api.app import app
from src.db.session import init_db
from src.db.seed import seed_database

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_api_test_db():
    init_db()
    seed_database()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "eventpilot-ai"

def test_rest_create_event_and_flow():
    # 1. Create Event
    event_payload = {
        "title": "REST Robotics Workshop 2026",
        "target_date": (datetime.now(timezone.utc) + timedelta(days=25)).isoformat(),
        "venue": "Robotics Lab 3",
        "capacity": 60,
        "budget": 20000.0,
    }
    resp = client.post("/api/events", json=event_payload)
    assert resp.status_code == 200
    ev = resp.json()
    eid = ev["event_id"]
    assert ev["capacity"] == 60

    # 2. Generate Timeline
    t_resp = client.post(f"/api/events/{eid}/timeline")
    assert t_resp.status_code == 200
    tasks = t_resp.json()
    assert len(tasks) == 7

    # 3. Detect Risks (Should detect 20 kit shortage)
    risk_resp = client.get(f"/api/events/{eid}/risks")
    assert risk_resp.status_code == 200
    risks = risk_resp.json()
    assert len(risks) == 1
    alert = risks[0]
    assert alert["shortage"] == 20
    assert len(alert["mitigation_options"]) == 3

    # 4. Mitigate Risk with Option B
    mit_payload = {
        "chosen_option_key": "OPTION_B",
        "approver_name": "API Test Admin",
    }
    mit_resp = client.post(f"/api/risks/{alert['alert_id']}/mitigate", json=mit_payload)
    assert mit_resp.status_code == 200
    mit_data = mit_resp.json()
    assert mit_data["status"] == "MITIGATED"

    # 5. Register Attendee
    reg_payload = {
        "student_name": "Maya Lin",
        "student_email": "maya@lin.edu",
        "student_id": "CS888",
    }
    reg_resp = client.post(f"/api/events/{eid}/registrations", json=reg_payload)
    assert reg_resp.status_code == 200
    reg = reg_resp.json()
    assert reg["status"] == "CONFIRMED"
    assert reg["qr_token"] is not None

    # 6. QR Check-In
    checkin_payload = {
        "qr_token": reg["qr_token"],
        "device_id": "REST_GATE_SCANNER",
    }
    checkin_resp = client.post("/api/attendance/checkin", json=checkin_payload)
    assert checkin_resp.status_code == 200
    checkin_data = checkin_resp.json()
    assert checkin_data["success"] is True
    assert checkin_data["student_name"] == "Maya Lin"

    # 7. Check Dashboard
    dash_resp = client.get(f"/api/events/{eid}/dashboard")
    assert dash_resp.status_code == 200
    dash = dash_resp.json()
    assert dash["confirmed_attendees"] == 1
    assert dash["capacity"] == 60
