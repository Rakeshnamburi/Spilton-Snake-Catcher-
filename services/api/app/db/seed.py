"""Create explicitly fictional demo records. No real contact data is inserted.

Alongside the demo admin/citizen, this seed also creates:
  * a small, clearly-labelled DEMO location directory (Telangana / Hyderabad),
    because the booking flow needs a state + district to select, and the real
    LGD directory is import-only; and
  * two fictional, verified, AVAILABLE demo rescuers so the nearby-rescuer
    discovery and booking flow can actually be tried locally.

Every row written here is marked with source_version / is_demo so it can never
be mistaken for official LGD data or a real responder.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.entities import (
    AvailabilityStatus,
    District,
    Incident,
    IncidentEvent,
    Organization,
    RescuerProfile,
    Role,
    State,
    Subdistrict,
    User,
    VerificationStatus,
)
from app.services.notifications import ensure_templates

DEMO_PASSWORD = "ChangeThisDemo123!"
DEMO_ADMIN_EMAIL = "admin.demo@spilton-demo.example"
DEMO_CITIZEN_EMAIL = "citizen.demo@spilton-demo.example"
DEMO_SOURCE_VERSION = "demo-seed-not-official-lgd"

DEMO_STATES = [
    # lgd_code, name
    ("36", "Telangana"),
]
DEMO_DISTRICTS = [
    # lgd_code, state_code, name  (real LGD codes for Telangana)
    ("507", "36", "Hyderabad"),
    ("518", "36", "Ranga Reddy"),
]
DEMO_SUBDISTRICTS = [
    # lgd_code, district_code, name  (real LGD mandal codes)
    ("4497", "507", "Ameerpet"),
    ("6319", "518", "Abdullapurmet"),
]
DEMO_LOCATION = {"state_code": "36", "district_code": "507", "subdistrict_code": "4497"}

DEMO_ORGANIZATION = {
    "name": "SPILTON Demo Wildlife Response (Fictional)",
    "state": "Telangana",
    "district": "Hyderabad",
    "organization_type": "WILDLIFE_RESPONSE",
}

DEMO_RESCUERS = [
    {
        "name": "Ravi Kumar (Demo Rescuer)",
        "email": "rescuer.ravi.demo@spilton-demo.example",
        "phone": "9000000011",
        "display_name": "Ravi K. — Demo Rescuer",
        "years_experience": 7,
        "languages": ["en", "te"],
        "latitude": 17.3850,
        "longitude": 78.4867,
        "rating": "4.70",
        "reviews": 18,
        "completed": 12,
    },
    {
        "name": "Anitha Reddy (Demo Rescuer)",
        "email": "rescuer.anitha.demo@spilton-demo.example",
        "phone": "9000000012",
        "display_name": "Anitha R. — Demo Rescuer",
        "years_experience": 4,
        "languages": ["en", "te", "hi"],
        "latitude": 17.4400,
        "longitude": 78.3489,
        "rating": "4.40",
        "reviews": 9,
        "completed": 5,
    },
]


def _ensure_locations(db) -> None:
    for code, name in DEMO_STATES:
        if not db.scalar(select(State).where(State.lgd_code == code)):
            db.add(State(lgd_code=code, name=name, source_version=DEMO_SOURCE_VERSION))
    db.flush()
    for code, state_code, name in DEMO_DISTRICTS:
        if not db.scalar(select(District).where(District.lgd_code == code)):
            db.add(
                District(
                    lgd_code=code,
                    state_code=state_code,
                    name=name,
                    source_version=DEMO_SOURCE_VERSION,
                )
            )
    db.flush()
    for code, district_code, name in DEMO_SUBDISTRICTS:
        if not db.scalar(select(Subdistrict).where(Subdistrict.lgd_code == code)):
            db.add(
                Subdistrict(
                    lgd_code=code,
                    district_code=district_code,
                    name=name,
                    source_version=DEMO_SOURCE_VERSION,
                )
            )
    db.flush()


def _ensure_organization(db) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.name == DEMO_ORGANIZATION["name"])
    )
    if organization is None:
        organization = Organization(
            **DEMO_ORGANIZATION,
            verification_status=VerificationStatus.VERIFIED,
        )
        db.add(organization)
        db.flush()
    else:
        organization.verification_status = VerificationStatus.VERIFIED
    return organization


def _ensure_rescuers(db, organization: Organization) -> None:
    """Create (or refresh) the fictional demo rescuers.

    Refreshing on every run keeps them AVAILABLE and their last_seen_at current,
    so the nearby search finds them again after the seed is re-run.
    """

    now = datetime.now(timezone.utc)
    for spec in DEMO_RESCUERS:
        user = db.scalar(select(User).where(User.email == spec["email"]))
        if user is None:
            user = User(
                name=spec["name"],
                email=spec["email"],
                phone=spec["phone"],
                password_hash=hash_password(DEMO_PASSWORD),
                role=Role.RESCUER,
            )
            db.add(user)
            db.flush()

        profile = db.scalar(select(RescuerProfile).where(RescuerProfile.user_id == user.id))
        if profile is None:
            profile = RescuerProfile(user_id=user.id)
            db.add(profile)

        profile.organization_id = organization.id
        profile.verification_status = VerificationStatus.VERIFIED
        profile.public_display_name = spec["display_name"]
        profile.state_code = DEMO_LOCATION["state_code"]
        profile.district_code = DEMO_LOCATION["district_code"]
        profile.subdistrict_code = DEMO_LOCATION["subdistrict_code"]
        profile.organization_name = organization.name
        profile.years_experience = spec["years_experience"]
        profile.languages = spec["languages"]
        profile.training_details = "Fictional demo record for local testing only."
        profile.authorization_reference = "DEMO-AUTH-0001"
        profile.issuing_authority = "Fictional Demo Wildlife Authority"
        profile.authorization_issue_date = date.today() - timedelta(days=365)
        profile.authorization_expiry = date.today() + timedelta(days=365)
        profile.service_area_description = "Demo service area around central Hyderabad."
        profile.service_radius_km = 30.0
        profile.latitude = spec["latitude"]
        profile.longitude = spec["longitude"]
        profile.availability = AvailabilityStatus.AVAILABLE
        profile.availability_updated_at = now
        profile.last_seen_at = now
        profile.average_rating = spec["rating"]
        profile.review_count = spec["reviews"]
        profile.completed_service_count = spec["completed"]
        profile.is_demo = True
    db.flush()


def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_templates(db)

        _ensure_locations(db)
        organization = _ensure_organization(db)
        _ensure_rescuers(db, organization)

        admin = db.scalar(select(User).where(User.email == DEMO_ADMIN_EMAIL))
        if admin is None:
            admin = User(
                name="Fictional Demo Admin",
                email=DEMO_ADMIN_EMAIL,
                phone="9000000001",
                password_hash=hash_password(DEMO_PASSWORD),
                role=Role.ADMIN,
            )
            db.add(admin)

        citizen = db.scalar(select(User).where(User.email == DEMO_CITIZEN_EMAIL))
        if citizen is None:
            citizen = User(
                name="Fictional Demo Citizen",
                email=DEMO_CITIZEN_EMAIL,
                phone="9000000002",
                password_hash=hash_password(DEMO_PASSWORD),
                role=Role.CITIZEN,
            )
            db.add(citizen)

        db.flush()

        existing_incident = db.scalar(
            select(Incident).where(Incident.reference_code == "SPR-DEMO-000001")
        )
        if existing_incident is None:
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
                    details=(
                        "Fictional demo incident seeded locally; no responder was dispatched."
                    ),
                )
            )

        db.commit()
        print("Demo data ready:")
        print(f"  admin    : {DEMO_ADMIN_EMAIL} / {DEMO_PASSWORD}")
        print(f"  citizen  : {DEMO_CITIZEN_EMAIL} / {DEMO_PASSWORD}")
        for spec in DEMO_RESCUERS:
            print(f"  rescuer  : {spec['email']} / {DEMO_PASSWORD}")
        print("  locations: Telangana / Hyderabad (demo directory)")


if __name__ == "__main__":
    seed()
