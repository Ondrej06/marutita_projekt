"""
seed_test_data.py
=================
Skript pro vytvoření testovacích uživatelů s reálnými bcrypt hesly.

Použití:
    1. Spusťte server: python app.py   (vytvoří databázi)
    2. Spusťte seed:   python seed_test_data.py

Vytvoří uživatele:
    emil   / password123
    gragas / password123
    garen  / password123

Pokud uživatel již existuje, přeskočí ho (bezpečné opakovat).
"""

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

DB_PATH = os.path.join(ROOT, "instance", "users.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "tajny_klic"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    __tablename__ = "user"
    id                = db.Column(db.Integer, primary_key=True)
    username          = db.Column(db.String(50),  unique=True, nullable=False)
    email             = db.Column(db.String(150), unique=True, nullable=False)
    password          = db.Column(db.String(150), nullable=False)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin          = db.Column(db.Boolean, default=False)
    enemies_killed    = db.Column(db.Integer, default=0)
    player_collisions = db.Column(db.Integer, default=0)
    projectiles_fired = db.Column(db.Integer, default=0)
    projectiles_hit   = db.Column(db.Integer, default=0)
    time_played       = db.Column(db.Float,   default=0.0)


class GameSession(db.Model):
    __tablename__ = "game_session"
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    timestamp         = db.Column(db.DateTime, default=datetime.utcnow)
    enemies_killed    = db.Column(db.Integer, default=0)
    player_collisions = db.Column(db.Integer, default=0)
    projectiles_fired = db.Column(db.Integer, default=0)
    projectiles_hit   = db.Column(db.Integer, default=0)
    time_played       = db.Column(db.Float,   default=0.0)


class Achievement(db.Model):
    __tablename__ = "achievement"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    icon        = db.Column(db.String(10),  default="trophy")


class UserAchievement(db.Model):
    __tablename__ = "user_achievement"
    user_id        = db.Column(db.Integer, db.ForeignKey("user.id",        ondelete="CASCADE"), primary_key=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievement.id", ondelete="CASCADE"), primary_key=True)
    unlocked_at    = db.Column(db.DateTime, default=datetime.utcnow)


TEST_USERS = [
    {
        "username": "emil",   "email": "emil@example.com",   "password": "password123",
        "enemies_killed": 150, "player_collisions": 12, "projectiles_fired": 800, "projectiles_hit": 450, "time_played": 3600.5,
        "sessions": [
            {"enemies_killed": 25, "player_collisions": 2, "projectiles_fired": 120, "projectiles_hit": 60,  "time_played": 320.5},
            {"enemies_killed": 30, "player_collisions": 3, "projectiles_fired": 150, "projectiles_hit": 75,  "time_played": 410.2},
        ],
        "achievements": ["Prvni krev", "Ostrostrelec"],
    },
    {
        "username": "gragas", "email": "gragas@example.com", "password": "password123",
        "enemies_killed": 42,  "player_collisions":  8, "projectiles_fired": 320, "projectiles_hit": 180, "time_played": 1250.0,
        "sessions": [
            {"enemies_killed": 12, "player_collisions": 2, "projectiles_fired": 70, "projectiles_hit": 30, "time_played": 210.8},
            {"enemies_killed":  8, "player_collisions": 1, "projectiles_fired": 45, "projectiles_hit": 18, "time_played": 145.3},
            {"enemies_killed": 15, "player_collisions": 3, "projectiles_fired": 85, "projectiles_hit": 35, "time_played": 270.1},
        ],
        "achievements": ["Prvni krev"],
    },
    {
        "username": "garen",  "email": "garen@example.com",  "password": "password123",
        "enemies_killed": 27,  "player_collisions":  5, "projectiles_fired": 210, "projectiles_hit":  95, "time_played":  980.2,
        "sessions": [
            {"enemies_killed": 10, "player_collisions": 2, "projectiles_fired": 55, "projectiles_hit": 22, "time_played": 180.5},
            {"enemies_killed":  9, "player_collisions": 1, "projectiles_fired": 48, "projectiles_hit": 20, "time_played": 165.9},
        ],
        "achievements": ["Prvni krev", "Nezranitelny"],
    },
]


def seed():
    if not os.path.exists(DB_PATH):
        print(f"Databaze nenalezena: {DB_PATH}")
        print("Nejprve spustte: python app.py")
        sys.exit(1)

    with app.app_context():
        created = 0
        skipped = 0

        for data in TEST_USERS:
            if User.query.filter_by(username=data["username"]).first():
                print(f"  {data['username']} jiz existuje, preskakuji.")
                skipped += 1
                continue

            hashed = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
            user = User(
                username=data["username"], email=data["email"], password=hashed,
                enemies_killed=data["enemies_killed"], player_collisions=data["player_collisions"],
                projectiles_fired=data["projectiles_fired"], projectiles_hit=data["projectiles_hit"],
                time_played=data["time_played"],
            )
            db.session.add(user)
            db.session.flush()

            for s in data["sessions"]:
                db.session.add(GameSession(user_id=user.id, **s))

            for ach_name in data["achievements"]:
                ach = Achievement.query.filter_by(name=ach_name).first()
                if ach:
                    db.session.add(UserAchievement(user_id=user.id, achievement_id=ach.id))

            print(f"  OK: {data['username']} vytvorenI (heslo: {data['password']})")
            created += 1

        db.session.commit()
        print(f"\nHotovo: {created} vytvoreno, {skipped} preskoceno.")


if __name__ == "__main__":
    print("Bubble Shooter -- seed testovacich uzivatelu")
    print("=" * 45)
    seed()