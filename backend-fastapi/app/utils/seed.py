"""
utils/seed.py — Seed initial MySQL data for NCC website
Runs automatically on first startup if tables are empty.
"""

from datetime import datetime
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.auth.jwt import hash_password


async def seed_initial_data():
    """Insert demo data only if tables are empty."""
    async with AsyncSessionLocal() as db:
        from app.models.orm_models import (
            User, Notice, Achievement, Camp, CadetPoints, Event, GalleryItem
        )

        # ── Admin user ────────────────────────────────────────────────────────
        user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
        if user_count == 0:
            admin = User(
                username="admin",
                email="admin@gph.edu.in",
                password_hash=hash_password("ncc@admin123"),
                role="admin",
                created_at=datetime.utcnow()
            )
            db.add(admin)
            print("Admin user created: admin@gph.edu.in / ncc@admin123")

        # ── Notices ───────────────────────────────────────────────────────────
        notice_count = (await db.execute(select(func.count()).select_from(Notice))).scalar()
        if notice_count == 0:
            notices = [
                Notice(title="CATC Camp Registration Open – Batch 2025",
                       category="Camp", description="All interested cadets must submit applications by 20th March 2025. Camp at NCC Training Centre, Hamirpur. Contact ANO for forms.",
                       issued_by="ANO Office", deadline="20 March 2025", is_new=True,
                       created_at=datetime(2025, 3, 10)),
                Notice(title="B Certificate Examination Schedule – 2025",
                       category="Exam", description="B Certificate examination for eligible 2nd year cadets on 25th April 2025. Minimum 75% attendance required.",
                       issued_by="Group HQ Hamirpur", deadline="25 April 2025", is_new=True,
                       created_at=datetime(2025, 3, 7)),
                Notice(title="Annual Inspection – 15th April 2025",
                       category="General", description="All cadets must attend Annual Inspection in No. 1 dress uniform. Mandatory attendance. Practice drills from 1st April.",
                       issued_by="ANO Office", is_new=False,
                       created_at=datetime(2025, 3, 5)),
                Notice(title="Blood Donation Camp – 22 March 2025",
                       category="Social", description="Annual blood donation camp with Civil Hospital Hamirpur. All cadets above 18 encouraged to participate. Participation certificate provided.",
                       issued_by="Social Service Cell", is_new=False,
                       created_at=datetime(2025, 2, 28)),
                Notice(title="Thal Sainik Camp (TSC) Selection Trials",
                       category="Camp", description="TSC 2025 selection trials on 10th March. Register at ANO office by 5th March. Physical standards and syllabus available on request.",
                       issued_by="ANO Office", deadline="05 March 2025", is_new=False,
                       created_at=datetime(2025, 2, 20)),
                Notice(title="New Enrollment Open – Academic Year 2025-26",
                       category="General", description="Enrollment for new cadets for 2025-26 is now open. First-year students can apply online or at ANO office. Limited seats.",
                       issued_by="ANO Office", is_new=True,
                       created_at=datetime(2025, 2, 10)),
            ]
            for n in notices:
                db.add(n)
            print(f"{len(notices)} notices seeded")

        # ── Achievements ──────────────────────────────────────────────────────
        ach_count = (await db.execute(select(func.count()).select_from(Achievement))).scalar()
        if ach_count == 0:
            achievements = [
                Achievement(cadet_name="Rahul Sharma", title="Republic Day Camp (RDC) Representative",
                            description="Selected to represent Himachal Pradesh at Republic Day Camp, New Delhi. Participated in the parade on Kartavya Path.",
                            year=2024, level="National", created_at=datetime.utcnow()),
                Achievement(cadet_name="Priya Thakur", title="Best Cadet – State Level NIC",
                            description="Awarded Best All-Round Cadet at National Integration Camp, Dharamshala.",
                            year=2024, level="State", created_at=datetime.utcnow()),
                Achievement(cadet_name="Amit Verma", title="Thal Sainik Camp Excellence Award",
                            description="Secured first position in military skills at TSC 2023.",
                            year=2023, level="National", created_at=datetime.utcnow()),
                Achievement(cadet_name="Sanjay Kumar", title="A Certificate – Distinction",
                            description="Passed A Certificate examination with distinction (90%+).",
                            year=2023, level="State", created_at=datetime.utcnow()),
                Achievement(cadet_name="Deepa Rana", title="B Certificate – Distinction",
                            description="Outstanding performance in B Certificate examination.",
                            year=2023, level="State", created_at=datetime.utcnow()),
                Achievement(cadet_name="Vikram Singh", title="YEP – Youth Exchange Programme",
                            description="Represented India at Youth Exchange Programme in Nepal.",
                            year=2022, level="International", created_at=datetime.utcnow()),
            ]
            for a in achievements:
                db.add(a)
            print(f"{len(achievements)} achievements seeded")

        # ── Camps ─────────────────────────────────────────────────────────────
        camp_count = (await db.execute(select(func.count()).select_from(Camp))).scalar()
        if camp_count == 0:
            camps = [
                Camp(name="Annual Training Camp (ATC) 2025", location="Hamirpur, HP",
                     camp_type="ATC", start_date="2025-05-01", end_date="2025-05-10",
                     description="Annual 10-day training camp for all cadets. Physical training, drill, academics, and cultural activities.",
                     is_upcoming=True, capacity=60, registered_count=0, created_at=datetime.utcnow()),
                Camp(name="CATC – Combined Annual Training Camp", location="NTC Hamirpur",
                     camp_type="CATC", start_date="2025-04-01", end_date="2025-04-10",
                     description="Combined Annual Training Camp mandatory for B/C certificate exam eligibility.",
                     is_upcoming=True, capacity=50, registered_count=18, created_at=datetime.utcnow()),
                Camp(name="Republic Day Camp 2025", location="New Delhi",
                     camp_type="RDC", start_date="2025-01-01", end_date="2025-01-28",
                     description="National level camp. Selected cadets represent Himachal Pradesh at Kartavya Path parade.",
                     is_upcoming=False, capacity=5, registered_count=2, created_at=datetime.utcnow()),
            ]
            for camp in camps:
                db.add(camp)
            print(f"{len(camps)} camps seeded")

        # ── Leaderboard (CadetPoints) ─────────────────────────────────────────
        lb_count = (await db.execute(select(func.count()).select_from(CadetPoints))).scalar()
        if lb_count == 0:
            leaders = [
                CadetPoints(cadet_name="Rahul Sharma", branch="CSE", points=980, rank_pos=1),
                CadetPoints(cadet_name="Priya Thakur", branch="EE", points=920, rank_pos=2),
                CadetPoints(cadet_name="Amit Verma", branch="ME", points=875, rank_pos=3),
                CadetPoints(cadet_name="Deepa Rana", branch="Civil", points=840, rank_pos=4),
                CadetPoints(cadet_name="Sanjay Kumar", branch="CSE", points=810, rank_pos=5),
                CadetPoints(cadet_name="Vikram Singh", branch="EE", points=780, rank_pos=6),
                CadetPoints(cadet_name="Neha Sharma", branch="ME", points=750, rank_pos=7),
                CadetPoints(cadet_name="Rohit Thakur", branch="Civil", points=720, rank_pos=8),
            ]
            for l in leaders:
                db.add(l)
            print(f"{len(leaders)} leaderboard entries seeded")

        # ── Events ────────────────────────────────────────────────────────────
        ev_count = (await db.execute(select(func.count()).select_from(Event))).scalar()
        if ev_count == 0:
            events = [
                Event(title="CATC Camp 2025", description="Combined Annual Training Camp",
                      event_type="Camp", start_date=datetime(2025, 4, 1), end_date=datetime(2025, 4, 10),
                      location="NTC Hamirpur", is_mandatory=True, created_at=datetime.utcnow()),
                Event(title="Annual Inspection", description="Annual unit inspection by commanding officer",
                      event_type="Parade", start_date=datetime(2025, 4, 15), end_date=datetime(2025, 4, 15),
                      location="College Parade Ground", is_mandatory=True, created_at=datetime.utcnow()),
                Event(title="Blood Donation Camp", description="Annual blood donation drive with Civil Hospital",
                      event_type="Social", start_date=datetime(2025, 3, 22), end_date=datetime(2025, 3, 22),
                      location="Civil Hospital, Hamirpur", is_mandatory=False, created_at=datetime.utcnow()),
                Event(title="B Certificate Exam", description="B Certificate final examination",
                      event_type="Exam", start_date=datetime(2025, 4, 25), end_date=datetime(2025, 4, 25),
                      location="GPH Campus", is_mandatory=False, created_at=datetime.utcnow()),
                Event(title="ATC 2025", description="Annual Training Camp for all cadets",
                      event_type="Camp", start_date=datetime(2025, 5, 1), end_date=datetime(2025, 5, 10),
                      location="Hamirpur, HP", is_mandatory=True, created_at=datetime.utcnow()),
            ]
            for ev in events:
                db.add(ev)
            print(f"{len(events)} events seeded")

        await db.commit()
        print("Database seeding complete.")
