"""
seed.py – Populate the NCC database with sample data.
Run once after creating the database:
    cd backend
    python seed.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import db, User, Notice, GalleryItem, Camp, Achievement, ContactMessage
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def seed():
    with app.app_context():
        db.create_all()

        # ── Admin User ─────────────────────────────────────────────────────
        if not User.query.filter_by(email='admin@ncc-gph.ac.in').first():
            admin = User(
                username      = 'ANO_Admin',
                email         = 'admin@ncc-gph.ac.in',
                password_hash = generate_password_hash('NCC@Admin2025', method='pbkdf2:sha256'),
                is_admin      = True,
            )
            db.session.add(admin)
            print('✅  Admin user created  –  admin@ncc-gph.ac.in  /  NCC@Admin2025')
        else:
            print('ℹ️   Admin user already exists.')

        # ── Notices ────────────────────────────────────────────────────────
        if Notice.query.count() == 0:
            notices = [
                Notice(
                    title       = 'Annual Training Camp 2025 – Registration Open',
                    category    = 'Camp',
                    description = 'Cadets interested in attending the Annual Training Camp (ATC) 2025 at Hamirpur must register before 25th March 2025. Carry NCC ID, two passport photos and medical fitness certificate.',
                    issued_by   = 'ANO Office',
                    deadline    = datetime.utcnow() + timedelta(days=14),
                    is_new      = True,
                ),
                Notice(
                    title       = 'Republic Day Parade 2025 – Selection Trials',
                    category    = 'Urgent',
                    description = 'Selection trials for Republic Day Parade contingent will be held on 10th April 2025 at College Parade Ground. All Army Wing cadets are compulsorily required to attend.',
                    issued_by   = 'ANO Lt. (Retd.) R.K. Sharma',
                    is_new      = True,
                ),
                Notice(
                    title       = 'Combined Annual Training Camp – Manali',
                    category    = 'Camp',
                    description = 'A Combined Annual Training Camp (CATC) will be conducted at Manali from 5-15 May 2025. Only A Certificate holders are eligible. Transport and accommodation will be provided.',
                    issued_by   = 'HQ 3 HP BN NCC',
                    is_new      = True,
                ),
                Notice(
                    title       = 'NCC "B" Certificate Exam – April 2025',
                    category    = 'Exam',
                    description = 'Written and practical examination for the NCC "B" Certificate will be conducted in the last week of April 2025. Cadets must have completed minimum 75% attendance.',
                    issued_by   = 'Examining Body',
                    deadline    = datetime.utcnow() + timedelta(days=30),
                    is_new      = False,
                ),
                Notice(
                    title       = 'Blood Donation Camp – World Health Day',
                    category    = 'Social',
                    description = 'NCC Unit is organising a Blood Donation Camp in collaboration with IGMC Shimla on 7th April 2025. All volunteers must be between 18-60 years and weigh over 55 kg.',
                    issued_by   = 'Social Service Committee',
                    is_new      = False,
                ),
                Notice(
                    title       = 'Trekking Expedition – Pin Parvati Pass',
                    category    = 'Camp',
                    description = 'NCC Adventure Activity – Trekking Expedition to Pin Parvati Pass (5319 m) scheduled for June 2025. Interested cadets should apply by 20th April with medical fitness certificate.',
                    issued_by   = 'Adventure Wing, HPU',
                    is_new      = False,
                ),
            ]
            db.session.add_all(notices)
            print(f'✅  {len(notices)} notices seeded.')

        # ── Gallery Items ──────────────────────────────────────────────────
        if GalleryItem.query.count() == 0:
            gallery = [
                GalleryItem(title='Republic Day Parade 2024', category='Parade',
                            description='NCC Cadets march during Republic Day at College Ground',
                            image_path='gallery_event1.webp'),
                GalleryItem(title='Annual Training Camp', category='Camps',
                            description='Cadets during ATC at Hamirpur',
                            image_path='gallery_event2.webp'),
                GalleryItem(title='Social Service Drive', category='Social',
                            description='Cleaning campaign at nearby village',
                            image_path='gallery_event3.webp'),
                GalleryItem(title='Independence Day Celebration', category='Parade',
                            description='Flag hoisting ceremony at college campus',
                            image_path='gallery_event4.webp'),
            ]
            db.session.add_all(gallery)
            print(f'✅  {len(gallery)} gallery items seeded.')

        # ── Camps ──────────────────────────────────────────────────────────
        if Camp.query.count() == 0:
            camps = [
                Camp(name='Annual Training Camp 2025', location='Hamirpur, HP',
                     camp_type='Annual Training', start_date='2025-04-10',
                     end_date='2025-04-20',
                     description='Annual training camp for all enrolled cadets. Covers drill, weapon training, map reading and leadership activities.',
                     is_upcoming=True),
                Camp(name='Combined Annual Training Camp – Manali', location='Manali, HP',
                     camp_type='Combined Annual', start_date='2025-05-05',
                     end_date='2025-05-15',
                     description='Multi-unit combined training camp in Manali with students from 5 colleges. Activities include mountaineering and cultural exchange.',
                     is_upcoming=True),
                Camp(name='Republic Day Camp 2024', location='Chandigarh',
                     camp_type='Republic Day', start_date='2024-01-10',
                     end_date='2024-01-26',
                     description='State-level Republic Day parade contingent training camp. Three cadets from our unit were selected.',
                     is_upcoming=False),
                Camp(name='Adventure Trekking – Rohtang', location='Rohtang Pass, HP',
                     camp_type='Adventure', start_date='2024-06-15',
                     end_date='2024-06-20',
                     description='High-altitude trekking expedition to Rohtang Pass (3978 m). Participated by 12 cadets.',
                     is_upcoming=False),
            ]
            db.session.add_all(camps)
            print(f'✅  {len(camps)} camps seeded.')

        # ── Achievements ───────────────────────────────────────────────────
        if Achievement.query.count() == 0:
            achievements = [
                Achievement(cadet_name='Suresh Kumar', title='Best Cadet Award – State Level',
                            description='Awarded Best All-Round NCC Cadet at 3 HP BN NCC annual function 2024.',
                            year=2024, level='State'),
                Achievement(cadet_name='Priya Sharma', title='Republic Day Parade – National Camp',
                            description='Selected for the National Republic Day Parade Camp at Delhi; part of the HP contingent.',
                            year=2024, level='National'),
                Achievement(cadet_name='Rahul Thakur', title='NCC "C" Certificate – Distinction',
                            description='Secured distinction in NCC C Certificate examination, the first cadet from the unit to do so.',
                            year=2023, level='State'),
                Achievement(cadet_name='Anjali Verma', title='Youth Exchange Program – Malaysia',
                            description='Selected for the International Youth Exchange Program to Malaysia under the NCC scheme.',
                            year=2024, level='International'),
                Achievement(cadet_name='Vikas Rana', title='Rock Climbing Champion',
                            description='Won Gold Medal in state-level rock climbing competition organised by NCC Directorate, HP.',
                            year=2023, level='State'),
            ]
            db.session.add_all(achievements)
            print(f'✅  {len(achievements)} achievements seeded.')

        db.session.commit()
        print('\n🎉  Database seeding completed successfully!')
        print('    ──────────────────────────────────')
        print('    Admin Login:  admin@ncc-gph.ac.in')
        print('    Password:     NCC@Admin2025')
        print('    Backend URL:  http://127.0.0.1:5000')


if __name__ == '__main__':
    seed()
