from flask import Flask, request, redirect, url_for, render_template, flash, jsonify  # přidáno jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# 🔹 Model uživatele
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    enemies_killed = db.Column(db.Integer, default=0)
    player_collisions = db.Column(db.Integer, default=0)
    projectiles_fired = db.Column(db.Integer, default=0)
    projectiles_hit = db.Column(db.Integer, default=0)
    time_played = db.Column(db.Float, default=0.0)
    
class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    enemies_killed = db.Column(db.Integer, default=0)
    player_collisions = db.Column(db.Integer, default=0)
    projectiles_fired = db.Column(db.Integer, default=0)
    projectiles_hit = db.Column(db.Integer, default=0)
    time_played = db.Column(db.Float, default=0.0)  # v sekundách

    user = db.relationship('User', backref=db.backref('sessions', lazy=True))

# ===== TENTO ENDPOINT JE JIŽ MIMO TŘÍDU A JE JEN JEDEN =====
@app.route("/api/update_stats", methods=["POST"])
def api_update_stats():
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({"error": "Missing user_id"}), 400

    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Aktualizace kumulativních statistik uživatele
    user.enemies_killed += data.get('enemies_killed', 0)
    user.player_collisions += data.get('player_collisions', 0)
    user.projectiles_fired += data.get('projectiles_fired', 0)
    user.projectiles_hit += data.get('projectiles_hit', 0)
    user.time_played += data.get('time_played', 0)

    # Vytvoření nového herního sezení
    session = GameSession(
        user_id=user.id,
        enemies_killed=data.get('enemies_killed', 0),
        player_collisions=data.get('player_collisions', 0),
        projectiles_fired=data.get('projectiles_fired', 0),
        projectiles_hit=data.get('projectiles_hit', 0),
        time_played=data.get('time_played', 0)
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({"success": True})

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# API endpoint pro registraci
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Chybí povinná pole"}), 400
    
    if User.query.filter((User.email == data['email']) | (User.username == data['username'])).first():
        return jsonify({"error": "Uživatel již existuje"}), 400
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        username=data['username'],
        email=data['email'],
        password=hashed_password
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Registrace proběhla úspěšně"
    }), 201

from sqlalchemy import func

@app.route("/")
def dashboard():
    if current_user.is_authenticated:
        users = User.query.all()

        if current_user.is_admin:
            # Admin: všechna sezení všech uživatelů
            sessions = db.session.query(GameSession, User).join(User, GameSession.user_id == User.id).order_by(GameSession.timestamp.desc()).all()
            best_stats = None  # pro admina nepotřebujeme
        else:
            # Všechny session všech uživatelů (pro tabulku)
            sessions = db.session.query(GameSession, User).join(User, GameSession.user_id == User.id).order_by(GameSession.timestamp.desc()).all()

            # Výpočet nejlepších statistik pro přihlášeného uživatele
            best_enemies = db.session.query(func.max(GameSession.enemies_killed)).filter_by(user_id=current_user.id).scalar() or 0
            best_collisions = db.session.query(func.max(GameSession.player_collisions)).filter_by(user_id=current_user.id).scalar() or 0
            best_fired = db.session.query(func.max(GameSession.projectiles_fired)).filter_by(user_id=current_user.id).scalar() or 0
            best_hit = db.session.query(func.max(GameSession.projectiles_hit)).filter_by(user_id=current_user.id).scalar() or 0
            best_time = db.session.query(func.max(GameSession.time_played)).filter_by(user_id=current_user.id).scalar() or 0.0

            best_accuracy = db.session.query(
                func.max(
                    (GameSession.projectiles_hit * 1.0 / 
                    func.nullif(GameSession.projectiles_fired, 0))
                )
            ).filter_by(user_id=current_user.id).scalar()
            if best_accuracy is None:
                best_accuracy = 0.0
            else:
                best_accuracy = best_accuracy * 100

            best_stats = {
                'enemies_killed': best_enemies,
                'player_collisions': best_collisions,
                'projectiles_fired': best_fired,
                'projectiles_hit': best_hit,
                'time_played': best_time,
                'accuracy': best_accuracy
            }
    else:
        users = []
        sessions = []
        best_stats = None

    return render_template("dashboard.html", users=users, sessions=sessions, best_stats=best_stats)

@app.route("/diagrams")
def diagrams():
    return render_template("diagrams.html")

# 🔹 Registrace
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode('utf-8')

        if User.query.filter((User.email==email) | (User.username==username)).first():
            flash("Uživatel s tímto emailem nebo username již existuje.", "danger")
            return redirect(url_for("register"))

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registrace proběhla úspěšně. Přihlašte se.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# 🔹 Přihlášení
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Chybí uživatelské jméno nebo heslo"}), 400
    
    login = data['username']   # parametr se jmenuje username, ale může to být email
    password = data['password']
    
    user = User.query.filter((User.username == login) | (User.email == login)).first()
    
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        })
    else:
        return jsonify({"error": "Neplatné přihlašovací údaje"}), 401
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Přihlášení proběhlo úspěšně.", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for("dashboard"))
        else:
            flash("Neplatný email nebo heslo.", "danger")
    return render_template("login.html")

# 🔹 Odhlášení
@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Byl jste odhlášen.", "info")
    return redirect(url_for("dashboard"))

# 🔹 Mazání uživatelů (jen admin)
@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Nemáte oprávnění smazat uživatele.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Uživatel {user.username} ({user.email}) byl smazán.', "success")
    return redirect(url_for('dashboard'))




if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # 🔹 Vytvoření admina pokud neexistuje
        if not User.query.filter_by(email="admin@example.com").first():
            admin_password = bcrypt.generate_password_hash("admin123").decode('utf-8')
            admin = User(username="admin", email="admin@example.com", password=admin_password, is_admin=True)
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)