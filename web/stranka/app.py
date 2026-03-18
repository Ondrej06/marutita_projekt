"""
app.py
======
Flask webový server — REST API, databázové modely a webové stránky.

Zodpovídá za:
  - Databázové modely (User, GameSession, Achievement, UserAchievement).
  - REST API pro přihlašování, registraci a ukládání herních statistik z Pygame.
  - Webové stránky (dashboard, diagramy, login, registrace).
  - Správu uživatelů adminem (mazání).
  - Automatické odemykání achievementů po každé hře.

Spuštění:
    python app.py
    Server poběží na http://127.0.0.1:5000

Výchozí admin účet (vytvoří se automaticky při prvním startu):
    Email: admin@example.com  |  Heslo: admin123
"""

from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from datetime import datetime
from sqlalchemy import func

# =============================================================================
# INICIALIZACE APLIKACE A ROZŠÍŘENÍ
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
# Cesta k SQLite databázi — Flask automaticky vytvoří složku instance/
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db            = SQLAlchemy(app)    # ORM pro práci s databází
bcrypt        = Bcrypt(app)        # Hashování hesel pomocí bcrypt algoritmu
login_manager = LoginManager(app)  # Správa přihlašovacích session na webu
login_manager.login_view = "login" # Přesměrování na /login při přístupu bez přihlášení


# =============================================================================
# DATABÁZOVÉ MODELY
# =============================================================================

class User(db.Model, UserMixin):
    """
    Model registrovaného uživatele.

    Dědí z UserMixin — poskytuje metody is_authenticated, is_active,
    get_id() potřebné pro Flask-Login.

    Kumulativní statistiky (enemies_killed atd.) jsou součet přes všechny hry.
    Jednotlivé herní záznamy jsou v tabulce GameSession (vztah 1:N).
    """
    id                = db.Column(db.Integer, primary_key=True)
    username          = db.Column(db.String(50),  unique=True, nullable=False)  # Unikátní přihlašovací jméno
    email             = db.Column(db.String(150), unique=True, nullable=False)  # Unikátní e-mail
    password          = db.Column(db.String(150), nullable=False)               # Bcrypt hash hesla
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)         # Čas registrace
    is_admin          = db.Column(db.Boolean, default=False)                    # Admin flag
    enemies_killed    = db.Column(db.Integer, default=0)   # Kumulativní počet zabitých nepřátel
    player_collisions = db.Column(db.Integer, default=0)   # Kumulativní počet kolizí
    projectiles_fired = db.Column(db.Integer, default=0)   # Kumulativní počet výstřelů
    projectiles_hit   = db.Column(db.Integer, default=0)   # Kumulativní počet zásahů
    time_played       = db.Column(db.Float,   default=0.0) # Celkový čas hraní v sekundách


class GameSession(db.Model):
    """
    Model jedné herní session — záznam jedné odehrané hry.

    Vztah 1:N s User: jeden uživatel může mít mnoho session.
    ON DELETE CASCADE zajistí, že při smazání uživatele se smažou
    i všechny jeho herní záznamy.
    """
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),  # CASCADE: smazání usera smaže i jeho session
        nullable=False
    )
    timestamp         = db.Column(db.DateTime, default=datetime.utcnow)  # Čas začátku hry
    enemies_killed    = db.Column(db.Integer, default=0)
    player_collisions = db.Column(db.Integer, default=0)
    projectiles_fired = db.Column(db.Integer, default=0)
    projectiles_hit   = db.Column(db.Integer, default=0)
    time_played       = db.Column(db.Float,   default=0.0)  # Délka hry v sekundách

    # Relationship: session.user a user.sessions (backref)
    # cascade='all, delete-orphan' zajišťuje mazání na úrovni SQLAlchemy ORM
    user = db.relationship(
        'User',
        backref=db.backref('sessions', lazy=True, cascade='all, delete-orphan')
    )


class Achievement(db.Model):
    """
    Model achievementu — jedna strana M:N vztahu s uživatelem.

    Achievementy jsou globální (sdílené všemi uživateli).
    Konkrétní odemčení pro uživatele je v tabulce UserAchievement.
    """
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)  # Unikátní název
    description = db.Column(db.String(255), nullable=False)               # Popis podmínky odemčení
    icon        = db.Column(db.String(10),  default='🏆')                 # Emoji ikona pro UI


class UserAchievement(db.Model):
    """
    Vazební tabulka realizující M:N vztah User <-> Achievement.

    Kompozitní primární klíč (user_id, achievement_id) zabraňuje
    duplicitnímu záznamu — uživatel nemůže získat stejný achievement dvakrát.
    Oba cizí klíče mají ON DELETE CASCADE.
    """
    __tablename__ = 'user_achievement'

    user_id        = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True  # Část kompozitního PK
    )
    achievement_id = db.Column(
        db.Integer,
        db.ForeignKey('achievement.id', ondelete='CASCADE'),
        primary_key=True  # Část kompozitního PK
    )
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)  # Čas odemčení

    user        = db.relationship('User',        backref=db.backref('user_achievements', lazy=True, cascade='all, delete-orphan'))
    achievement = db.relationship('Achievement', backref=db.backref('user_achievements', lazy=True))


# =============================================================================
# POMOCNÉ FUNKCE
# =============================================================================

def check_and_unlock_achievements(user: User) -> None:
    """
    Zkontroluje podmínky achievementů a odemkne splněné pro daného uživatele.

    Volá se po každém uložení herní session v api_update_stats().
    Pracuje s kumulativními statistikami uživatele (ne jednou session).

    Podmínky:
      "První krev"    — uživatel celkově zabil >= 1 nepřítele
      "Ostrostřelec"  — celková přesnost >= 80 %
      "Nezranitelný"  — 0 kolizí celkově a >= 5 zabitých nepřátel

    Args:
        user: Instance User, jejíž achievementy se kontrolují.
    """
    # Množina ID již odemčených achievementů — O(1) lookup při kontrole
    already_unlocked = {ua.achievement_id for ua in user.user_achievements}

    conditions = [
        ("První krev",
         user.enemies_killed >= 1),

        ("Ostrostřelec",
         user.projectiles_fired > 0
         and (user.projectiles_hit / user.projectiles_fired) >= 0.8),

        ("Nezranitelný",
         user.player_collisions == 0 and user.enemies_killed >= 5),
    ]

    for name, condition in conditions:
        if condition:
            achievement = Achievement.query.filter_by(name=name).first()
            # Odemkni pouze pokud achievement existuje a ještě není odemčen
            if achievement and achievement.id not in already_unlocked:
                db.session.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))


# =============================================================================
# REST API ENDPOINTY
# =============================================================================

@app.route("/api/update_stats", methods=["POST"])
def api_update_stats():
    """
    Uloží statistiky jedné herní session a aktualizuje celkové statistiky uživatele.

    Volá se z PlayingState.send_stats_to_server() po skončení každé hry.

    Očekávaný JSON payload:
        { "user_id": int, "enemies_killed": int, "player_collisions": int,
          "projectiles_fired": int, "projectiles_hit": int, "time_played": float }

    Returns:
        JSON {"success": True} nebo {"error": "..."} s příslušným HTTP kódem.
    """
    data = request.get_json()

    if not data or 'user_id' not in data:
        return jsonify({"error": "Missing user_id"}), 400

    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Přičtení hodnot k celkovým kumulativním statistikám uživatele
    user.enemies_killed    += data.get('enemies_killed', 0)
    user.player_collisions += data.get('player_collisions', 0)
    user.projectiles_fired += data.get('projectiles_fired', 0)
    user.projectiles_hit   += data.get('projectiles_hit', 0)
    user.time_played       += data.get('time_played', 0)

    # Vytvoření nového záznamu GameSession pro tuto konkrétní hru
    session = GameSession(
        user_id           = user.id,
        enemies_killed    = data.get('enemies_killed', 0),
        player_collisions = data.get('player_collisions', 0),
        projectiles_fired = data.get('projectiles_fired', 0),
        projectiles_hit   = data.get('projectiles_hit', 0),
        time_played       = data.get('time_played', 0)
    )
    db.session.add(session)
    db.session.commit()  # Commit před achievementy — statistiky musí být aktuální

    # Kontrola a odemčení achievementů na základě aktualizovaných statistik
    check_and_unlock_achievements(user)
    db.session.commit()

    return jsonify({"success": True})


@login_manager.user_loader
def load_user(user_id: str) -> User:
    """
    Callback pro Flask-Login — načte uživatele ze session cookie při každém požadavku.

    Args:
        user_id: ID uživatele jako řetězec (z cookie).

    Returns:
        User instance nebo None (= uživatel není přihlášen).
    """
    return User.query.get(int(user_id))


@app.route("/api/register", methods=["POST"])
def api_register():
    """
    REST API endpoint pro registraci nového uživatele (z externího klienta).

    Očekávaný JSON: {"username": str, "email": str, "password": str}

    Returns:
        JSON {"success": True} s HTTP 201 při úspěchu.
        JSON {"error": "..."} s HTTP 400 při chybě.
    """
    data = request.get_json()

    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Chybí povinná pole"}), 400

    # Kontrola duplicity — email nebo username již existuje v databázi
    if User.query.filter((User.email == data['email']) | (User.username == data['username'])).first():
        return jsonify({"error": "Uživatel již existuje"}), 400

    # Heslo se hashuje před uložením — nikdy neukládáme plaintext
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(username=data['username'], email=data['email'], password=hashed_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"success": True, "message": "Registrace proběhla úspěšně"}), 201


# =============================================================================
# WEBOVÉ STRÁNKY
# =============================================================================

@app.route("/")
def dashboard():
    """
    Hlavní stránka dashboardu se statistikami.

    Obsah závisí na roli uživatele:
      - Nepřihlášený: výzva k přihlášení, žádná data.
      - Přihlášený: všechny session (pro srovnání), osobní rekordy, achievementy.
      - Admin: tabulka všech uživatelů s mazáním + tabulka všech session.

    Nejlepší statistiky se počítají přes SQL MAX agregaci přímo v databázi.
    """
    if current_user.is_authenticated:
        users = User.query.all()

        if current_user.is_admin:
            # Admin: všechna sezení s JOIN na User (pro zobrazení username)
            sessions   = (db.session.query(GameSession, User)
                          .join(User, GameSession.user_id == User.id)
                          .order_by(GameSession.timestamp.desc()).all())
            best_stats = None  # Admin nepotřebuje osobní rekordy

        else:
            # Běžný uživatel: všechny session pro srovnání s ostatními hráči
            sessions = (db.session.query(GameSession, User)
                        .join(User, GameSession.user_id == User.id)
                        .order_by(GameSession.timestamp.desc()).all())

            # Nejlepší hodnoty aktuálního uživatele — SQL MAX agregační funkce
            best_enemies    = db.session.query(func.max(GameSession.enemies_killed)   ).filter_by(user_id=current_user.id).scalar() or 0
            best_collisions = db.session.query(func.max(GameSession.player_collisions)).filter_by(user_id=current_user.id).scalar() or 0
            best_fired      = db.session.query(func.max(GameSession.projectiles_fired)).filter_by(user_id=current_user.id).scalar() or 0
            best_hit        = db.session.query(func.max(GameSession.projectiles_hit)  ).filter_by(user_id=current_user.id).scalar() or 0
            best_time       = db.session.query(func.max(GameSession.time_played)      ).filter_by(user_id=current_user.id).scalar() or 0.0

            # Nejlepší přesnost: MAX(hits / shots) — NULLIF zabrání dělení nulou
            best_accuracy = db.session.query(
                func.max(GameSession.projectiles_hit * 1.0 /
                         func.nullif(GameSession.projectiles_fired, 0))
            ).filter_by(user_id=current_user.id).scalar()
            best_accuracy = (best_accuracy * 100) if best_accuracy else 0.0

            best_stats = {
                'enemies_killed':    best_enemies,
                'player_collisions': best_collisions,
                'projectiles_fired': best_fired,
                'projectiles_hit':   best_hit,
                'time_played':       best_time,
                'accuracy':          best_accuracy,
            }
    else:
        # Nepřihlášený host — prázdná data
        users = []; sessions = []; best_stats = None

    return render_template(
        "dashboard.html",
        users        = users,
        sessions     = sessions,
        best_stats   = best_stats,
        achievements = Achievement.query.all() if current_user.is_authenticated else []
    )


@app.route("/diagrams")
def diagrams():
    """Stránka s vývojovým diagramem a ER diagramem — přístupná bez přihlášení."""
    return render_template("diagrams.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Webový registrační formulář.

    GET:  Zobrazí prázdný formulář (register.html).
    POST: Zpracuje data — vytvoří uživatele nebo zobrazí chybu.
    """
    if request.method == "POST":
        username = request.form["username"]
        email    = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode('utf-8')

        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("Uživatel s tímto emailem nebo username již existuje.", "danger")
            return redirect(url_for("register"))

        db.session.add(User(username=username, email=email, password=password))
        db.session.commit()
        flash("Registrace proběhla úspěšně. Přihlašte se.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    """
    REST API přihlášení pro Pygame klienta (LoginState v states.py).

    Přijímá username nebo email. Ověří bcrypt hash a vrátí user data.

    Očekávaný JSON: {"username": str, "password": str}

    Returns:
        JSON s user daty (HTTP 200) nebo {"error": "..."} (HTTP 400/401).
    """
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Chybí uživatelské jméno nebo heslo"}), 400

    login_input = data['username']  # Může být username i e-mail
    password    = data['password']

    # Hledej podle username NEBO emailu — flexibilní přihlášení
    user = User.query.filter(
        (User.username == login_input) | (User.email == login_input)
    ).first()

    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        return jsonify({
            "success": True,
            "user": {"id": user.id, "username": user.username,
                     "email": user.email, "is_admin": user.is_admin}
        })
    else:
        return jsonify({"error": "Neplatné přihlašovací údaje"}), 401


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Webový přihlašovací formulář.

    GET:  Zobrazí formulář (login.html).
    POST: Ověří email + heslo; přihlásí a přesměruje na dashboard nebo ?next=.
    """
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]
        user     = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Přihlášení proběhlo úspěšně.", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for("dashboard"))
        else:
            flash("Neplatný email nebo heslo.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Odhlásí uživatele (smaže session cookie) a přesměruje na dashboard."""
    if current_user.is_authenticated:
        logout_user()
        flash("Byl jste odhlášen.", "info")
    return redirect(url_for("dashboard"))


@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id: int):
    """
    Smaže uživatele — pouze pro adminy.

    Díky ON DELETE CASCADE se automaticky smažou také všechny jeho
    GameSession a UserAchievement záznamy.

    Args:
        user_id: ID uživatele k smazání (z URL).
    """
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Nemáte oprávnění smazat uživatele.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Uživatel {user.username} ({user.email}) byl smazán.', "success")
    return redirect(url_for('dashboard'))


# =============================================================================
# SPUŠTĚNÍ SERVERU
# =============================================================================

if __name__ == "__main__":
    with app.app_context():
        # Vytvoří všechny tabulky (bezpečné opakovat — existující neupraví)
        db.create_all()

        # Seed výchozího admin účtu při prvním spuštění
        if not User.query.filter_by(email="admin@example.com").first():
            admin_password = bcrypt.generate_password_hash("admin123").decode('utf-8')
            admin = User(username="admin", email="admin@example.com",
                         password=admin_password, is_admin=True)
            db.session.add(admin)
            db.session.commit()

        # Seed achievementů — přidá chybějící, existující přeskočí
        for ach_data in [
            ("První krev",   "Zabij prvního nepřítele",               "🩸"),
            ("Ostrostřelec", "Dosáhni přesnosti nad 80 % v jedné hře","🎯"),
            ("Nezranitelný", "Dokonči hru bez jediné kolize",          "🛡️"),
        ]:
            if not Achievement.query.filter_by(name=ach_data[0]).first():
                db.session.add(Achievement(name=ach_data[0], description=ach_data[1], icon=ach_data[2]))
        db.session.commit()

    # debug=True: auto-reload při změně kódu, detailní chybové stránky
    # POZOR: nikdy nepoužívat debug=True v produkčním prostředí!
    app.run(debug=True)