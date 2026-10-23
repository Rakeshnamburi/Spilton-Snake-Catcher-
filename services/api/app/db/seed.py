"""Create explicitly fictional demo records. No real contact data is inserted."""

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.entities import Incident, IncidentEvent, Role, User
from app.services.notifications import ensure_templates

DEMO_ADMIN_EMAIL = "admin.demo@spilton-demo.example"
DEMO_CITIZEN_EMAIL = "citizen.demo@spilton-demo.example"


def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_templates(db)
        if db.query(User).filter_by(email=DEMO_ADMIN_EMAIL).first():
            db.commit()
            return
        admin = User(
            name="Fictional Demo Admin",
            email=DEMO_ADMIN_EMAIL,
            phone="9000000001",
            password_hash=hash_password("ChangeThisDemo123!"),
            role=Role.ADMIN,
        )
        citizen = User(
            name="Fictional Demo Citizen",
            email=DEMO_CITIZEN_EMAIL,
            phone="9000000002",
            password_hash=hash_password("ChangeThisDemo123!"),
            role=Role.CITIZEN,
        )
        db.add_all([admin, citizen])
        db.flush()
        incident = Incident(
            reference_code="SPR-DEMO-000001",
            reporter_id=citizen.id,
            reporter_name=citizen.name,
            contact_phone=citizen.phone,
            state="Telangana",
            district="Demo District",
            city="Demo Village",
            description="Fictional record used only to demonstrate the dashboard.",
            is_demo=True,
        )
        db.add(incident)
        db.flush()
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                actor_id=citizen.id,
                event_type="INCIDENT_CREATED",
                details="Fictional demo incident seeded locally; no responder was dispatched.",
            )
        )
        db.commit()


if __name__ == "__main__":
    seed()
