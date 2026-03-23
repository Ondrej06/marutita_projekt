
# Bubble Shooter

2D arénová střílečka v Pygame propojená s webovým dashboardem na Flask.

---

## 1. Požadavky

* Python **3.8 nebo novější**
* Pip (součást instalace Pythonu)
* Git (volitelně, pro klonování)

---

## 2. Stažení projektu

```bash
git clone https://github.com/Ondrej06/marutita_projekt.git
cd marutita_projekt
```

Nebo si stáhněte ZIP a rozbalte.

---

## 3. Instalace závislostí

Otevřete terminál ve složce projektu a spusťte:

```bash
pip install pygame flask flask-sqlalchemy flask-bcrypt flask-login requests
```

---

## 4. Spuštění serveru

Server je nutný pro ukládání statistik do databáze a pro přístup na web.

```bash
python app.py
```

Po spuštění uvidíte:

```
 * Running on http://127.0.0.1:5000
```

Nechte tento terminál otevřený. Server vytvoří databázi `instance/users.db` a výchozího administrátora:

* **Email:** admin@example.com
* **Heslo:** admin123

---

## 5. Spuštění hry

Otevřete **druhý terminál** ve stejné složce a spusťte:

```bash
python menu.py
```

Objeví se herní okno s úvodní obrazovkou. Po skončení hry se statistiky odešlou na server a uloží do databáze.

> **Poznámka:** Pokud server neběží, hra se spustí normálně, ale statistiky se ukládají pouze do lokálního souboru `game_stats.json`.

---

## 6. Přístup na web

Otevřete prohlížeč na adrese  **http://127.0.0.1:5000** . Zde lze:

* Registrovat nový účet
* Přihlásit se
* Prohlížet herní session všech hráčů
* Jako administrátor mazat uživatele
* Zobrazit diagramy a popis hry

---

## Struktura projektu

```
marutita_projekt/
├── Assets/                     # Grafické assety (back_1.png, font Orbitron)
├── instance/                   # Vytvoří Flask automaticky (users.db)
├── sql/
│   ├── create.sql              # DDL — vytvoření tabulek
│   ├── insert.sql              # Vzorová data (SQL ukázka, placeholder hesla)
│   ├── select.sql              # Ukázkové SELECT dotazy (JOIN, GROUP BY, filtrace)
│   └── update_delete.sql       # UPDATE a DELETE příkazy
├── web/
│   └── stranka/
│       ├── static/
│       │   └── style.css       # Styly webových stránek
│       └── templates/
│           ├── dashboard.html  # Šablona dashboardu
│           ├── diagrams.html   # Šablona stránky s diagramy
│           ├── login.html      # Šablona přihlášení
│           └── register.html   # Šablona registrace
├── app.py                      # Flask server — REST API, webové stránky, modely DB
├── menu.py                     # Hlavní vstupní bod — Pygame smyčka, StateManager
├── states.py                   # BaseState, ButtonMenuState, GameState enum
├── states_menu.py              # IntroState, MainMenuState, SettingsState, GraphicsState, LoginState
├── states_game.py              # PlayingState — herní logika, kolize, statistiky
├── player.py                   # Třída Player — pohyb, létání, dash, zdraví
├── enemy.py                    # Třída Enemy — pohyb, slow, dot efekty
├── projectiles.py              # Třída Projectile — fyzika, stopa, efekty
├── render.py                   # Renderer — HUD (zdraví, stamina, dash, FPS, overlay)
├── button.py                   # Button a InputBox — UI komponenty menu
├── utils.py                    # HelperFunctions — spawn, kolize, částice
├── visuals.py                  # Colors, FontCache, hvězdné pozadí
├── config.py                   # GameConfig a MenuConfig — všechny konstanty
├── settings.py                 # Načítání/ukládání config.json, cesty k souborům
├── seed_test_data.py           # Vytvoření testovacích uživatelů s bcrypt hesly
├── import_jsonDB.py            # Ruční import game_stats.json do databáze
├── run_sql.py                  # Nástroj pro spuštění SQL skriptů na databázi
├── game_stats.json             # Záložní statistiky (když server neběží)
├── config.json                 # Uživatelské nastavení (rozlišení, poslední uživatel)
└── Dokument.docx               # Projektová dokumentace
```

---

## Spuštění SQL skriptů

SQL skripty se spouštějí z kořenové složky projektu nástrojem `run_sql.py`:

```bash
python run_sql.py sql/create.sql        # Vytvoří tabulky
python run_sql.py sql/insert.sql        # Vloží vzorová data (SQL ukázka)
python run_sql.py sql/select.sql        # Ukázkové SELECT dotazy
python run_sql.py sql/update_delete.sql # UPDATE a DELETE příkazy
```

> Databáze musí existovat — nejprve spusťte `python app.py`.

### Testovací uživatelé s funkčním přihlášením

`insert.sql` obsahuje placeholder hesla (čistě pro SQL demonstraci).

Pro funkční testovací účty spusťte:

```bash
python seed_test_data.py
```

Vytvoří uživatele  **emil** ,  **gragas** , **garen** s heslem `password123`.

---

## Použité technologie

| Oblast                     | Knihovna / nástroj               |
| -------------------------- | --------------------------------- |
| Herní engine              | Pygame                            |
| Webový framework          | Flask                             |
| ORM / databáze            | Flask-SQLAlchemy + SQLite         |
| Hashování hesel          | Flask-Bcrypt                      |
| Správa session (web)      | Flask-Login                       |
| HTTP komunikace (hra→web) | Requests                          |
| Standardní knihovny       | math, random, threading, json, os |

---

## Diagramy

Na stránce **Diagramy** (dostupné z dashboardu) naleznete:

* **Vývojový diagram** — hlavní smyčka hry a přechody mezi stavy
* **ER diagram** — struktura databáze (User, GameSession, Achievement, UserAchievement)

---

## Autor

**Ondřej Novotný** — maturitní práce 2025/2026

---

## Časté problémy

| Problém                          | Řešení                                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------------------------ |
| `pip`není rozpoznán           | Použijte `python -m pip install ...`nebo přeinstalujte Python s volbou „Add Python to PATH" |
| Port 5000 je obsazený            | V `app.py`změňte na `app.run(port=5001)`, v `states_game.py`upravte `self.base_url`    |
| Hra se nespouští                | Ověřte:`pip install pygame`. Při problémech zkuste `pip install pygame==2.0.3`           |
| Statistiky se neukládají        | Zkontrolujte, zda běží server (`python app.py`); záloha jde do `game_stats.json`         |
| Import JSON selže                | Spusťte ručně:`python import_jsonDB.py`                                                     |
| `run_sql.py`nenajde databázi   | Nejprve spusťte server, který databázi vytvoří                                              |
| Testovací uživatelé nefungují | Spusťte `python seed_test_data.py`místo `insert.sql`pro funkční bcrypt hesla             |

---
