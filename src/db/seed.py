"""Seed script for EventPilot AI.
Seeds users, inventory items (specifically the 40 available Robotics Hardware Kits),
and historical metrics for demo runs.
"""
import logging
from datetime import datetime, timezone, timedelta
from src.db.session import SessionLocal, init_db
from src.db.models import (
    User,
    UserRole,
    InventoryItem,
    HistoricalEventMetric,
)

logger = logging.getLogger("eventpilot.seed")

def seed_database():
    """Populate database with baseline synthetic records."""
    init_db()
    db = SessionLocal()

    try:
        # 1. Seed Core Team Users
        users_data = [
            {"name": "Lead Organizer", "email": "organizer@college.edu", "role": UserRole.ORGANIZER},
            {"name": "Alex Rivera (Logistics)", "email": "logistics@college.edu", "role": UserRole.VOLUNTEER},
            {"name": "Sarah Chen (Registration)", "email": "registration@college.edu", "role": UserRole.VOLUNTEER},
            {"name": "Faculty Coordinator", "email": "faculty@college.edu", "role": UserRole.ADMIN},
        ]
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                db.add(User(**u))
        db.commit()

        # 2. Seed Equipment Inventory (CRITICAL: 40 Robotics Hardware Kits available)
        inventory_data = [
            {
                "name": "Robotics Hardware Kit",
                "category": "Robotics",
                "total_quantity": 40,
                "available_quantity": 40,  # 40 available vs 60 needed creates the deterministic 20 kit shortage!
                "unit_cost": 450.0,  # Grounded unit rental cost for ground calculations
                "location": "Robotics Lab Depot - Rack B",
            },
            {
                "name": "Soldering Station Kit",
                "category": "Electronics",
                "total_quantity": 25,
                "available_quantity": 25,
                "unit_cost": 300.0,
                "location": "Hardware Lab 1",
            },
            {
                "name": "Microcontroller Development Board",
                "category": "Embedded Systems",
                "total_quantity": 70,
                "available_quantity": 70,
                "unit_cost": 600.0,
                "location": "Storage Cabinet 3",
            },
        ]

        for item in inventory_data:
            existing_item = db.query(InventoryItem).filter(InventoryItem.name == item["name"]).first()
            if not existing_item:
                db.add(InventoryItem(**item))
            else:
                existing_item.available_quantity = item["available_quantity"]
                existing_item.total_quantity = item["total_quantity"]
                existing_item.unit_cost = item["unit_cost"]
        db.commit()

        # 3. Seed Historical Event Metrics for reference
        metrics_data = [
            {
                "event_title": "Fall 2025 Introductory Robotics",
                "event_type": "Robotics Workshop",
                "attendee_count": 50,
                "budget_allocated": 18000.0,
                "budget_spent": 16500.0,
                "kits_used": 25,
                "turnout_percentage": 94.0,
                "key_takeaways": "Pairing students 2 per kit increased collaboration and reduced equipment failure rates.",
            },
            {
                "event_title": "Spring 2026 Microcontroller Boot Camp",
                "event_type": "Technical Workshop",
                "attendee_count": 45,
                "budget_allocated": 15000.0,
                "budget_spent": 14200.0,
                "kits_used": 45,
                "turnout_percentage": 91.0,
                "key_takeaways": "Hands-on solo exercises require 10% spare components for burnt microcontrollers.",
            },
        ]

        for m in metrics_data:
            existing_m = db.query(HistoricalEventMetric).filter(
                HistoricalEventMetric.event_title == m["event_title"]
            ).first()
            if not existing_m:
                db.add(HistoricalEventMetric(**m))
        db.commit()

        print("[OK] Database successfully initialized and seeded with baseline inventory & metrics.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
