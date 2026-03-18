# marutita_projekt

### 1. Požadavky

- Python **3.8 nebo novější**
- Pip (součást instalace Pythonu)
- Git (volitelně, pro klonování)

### 2. Stažení projektu

```bash
git clone https://github.com/Ondrej06/marutita_projekt.git
cd marutita_projekt
nebo si stáhněte ZIP a rozbalte.

3. Instalace závislostí
Otevřete terminál ve složce projektu a spusťte:

bash
pip install pygame flask flask-sqlalchemy flask-bcrypt flask-login requests
Tento příkaz nainstaluje:

Pygame – herní engine

Flask – webový framework

Flask-SQLAlchemy – práce s databází

Flask-Bcrypt – hashování hesel

Flask-Login – správa uživatelských relací

Requests – komunikace mezi hrou a serverem

4. Spuštění serveru
Server je nutný pro ukládání statistik do databáze a pro přístup na web.

bash
python web/stranka/app.py
Po spuštění uvidíte:

text
 * Running on http://127.0.0.1:5000
Nechte tento terminál otevřený. Server vytvoří databázi users.db a výchozího administrátora:

Email: admin@example.com

Heslo: admin123

5. Spuštění hry
Otevřete druhý terminál (nové okno) ve stejné složce a spusťte:

bash
python menu.py
Objeví se herní okno s úvodní obrazovkou (Intro). Po skončení hry se statistiky odešlou na server a uloží do databáze.

Poznámka: Pokud server neběží, hra se spustí normálně, ale statistiky se ukládají pouze do lokálního souboru game_stats.json. Při příštím spuštění serveru se data automaticky importují.

6. Přístup na web
Otevřete prohlížeč a přejděte na adresu http://127.0.0.1:5000. Zde můžete:

Registrovat nový účet

Přihlásit se

Prohlížet všechny herní session (včetně ostatních hráčů)

Jako administrátor mazat uživatele

Zobrazit diagramy a podrobný popis hry

 Struktura projektu
text
marutita_projekt/
├── Assets/                 # Grafické assety (např. back_1.png)
├── sql/                    # SQL skripty (create, insert, select)
├── web/
│   └── stranka/
│       ├── static/         # CSS, obrázky (Flow.png, ERD.png)
│       ├── templates/      # HTML šablony (dashboard.html, diagrams.html, login.html, register.html)
│       └── app.py          # Flask server
├── button.py               # Třída pro tlačítka v Pygame
├── config.py               # Konfigurace hry a menu
├── enemy.py                # Třída nepřítele
├── game.py                 # Původní herní smyčka (lze spustit samostatně)
├── game_stats.json         # Lokální záloha statistik (když server neběží)
├── import_json_to_db.py    # Skript pro ruční import JSON do DB
├── menu.py                 # Hlavní spouštěcí soubor hry (s menu)
├── path.py                 # Cesty k souborům
├── player.py               # Třída hráče
├── projectiles.py          # Třída projektilu
├── render.py               # Vykreslování UI ve hře
├── states.py               # Stavy hry (intro, menu, hra, login, atd.)
├── utils.py                # Pomocné funkce
└── visuals.py              # Efekty (hvězdy, font cache)
 Použité technologie a knihovny
Hra
Pygame – herní engine

Math, Random, Threading – standardní knihovny

Web
Flask – webový framework

Flask-SQLAlchemy – ORM pro databázi

Flask-Bcrypt – hashování hesel

Flask-Login – správa uživatelských relací

Requests – HTTP komunikace z Pygame na Flask

Databáze
SQLite – databáze (soubor users.db)

SQLAlchemy – práce s DB přes Python

 Diagramy
Na stránce Diagramy (přístupné z dashboardu) naleznete:

Vývojový diagram – znázorňuje hlavní smyčku hry a přechody mezi stavy.

ER diagram – struktura databáze (tabulky User a GameSession).

Autor
Ondřej Novotný 

Projekt vznikl jako maturitní práce v roce 2025.

Licence
Tento projekt je určen pouze pro studijní účely. Všechna práva vyhrazena.

Časté problémy
pip není rozpoznán
Použijte python -m pip install ... nebo přeinstalujte Python a zaškrtněte Add Python to PATH.

Port 5000 je obsazený
V souboru app.py změňte:

python
app.run(debug=True, port=5001)
a v states.py upravte base_url na http://127.0.0.1:5001.

Hra se nespouští (chybí Pygame)
Ověřte instalaci: pip install pygame. Pokud problém přetrvává, zkuste starší verzi Pygame (pip install pygame==2.0.3).

Import JSON se nespustí automaticky
Pokud při startu serveru neproběhne import, spusťte ručně:

bash
python import_json_to_db.py
text

Tento README obsahuje vše potřebné – od popisu projektu, přes instalaci, až po strukturu a řešení problémů. Můžeš ho rovnou použít.
```
