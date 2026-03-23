-- ============================================================
-- POZOR: Tento soubor obsahuje ukázkové uživatele s PLACEHOLDER hesly.
-- Tito uživatelé slouží pouze k demonstraci SQL (JOIN, GROUP BY atd.)
-- a nepůjde se přes ně přihlásit.
--
-- Pro plně funkční testovací uživatele (s reálnými bcrypt hesly) spusťte:
--   python seed_test_data.py
-- (skript vytvoří uživatele emil, gragas, garen s heslem "password123")
-- ============================================================

-- Vyčištění předchozích testovacích dat (idempotentní spuštění)
-- CASCADE automaticky smaže i jejich game_session a user_achievement záznamy.
DELETE FROM user WHERE username IN ('emil', 'gragas', 'garen');

-- Vložení uživatelů
-- Hesla jsou placeholder — pro přihlášení použijte seed_test_data.py
INSERT INTO user (username, email, password, is_admin, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
VALUES 
    ('emil',   'emil@example.com',   '$2b$12$PLACEHOLDER_RUN_SEED_SCRIPT', 0, 150, 12, 800, 450, 3600.5),
    ('gragas', 'gragas@example.com', '$2b$12$PLACEHOLDER_RUN_SEED_SCRIPT', 0,  42,  8, 320, 180, 1250.0),
    ('garen',  'garen@example.com',  '$2b$12$PLACEHOLDER_RUN_SEED_SCRIPT', 0,  27,  5, 210,  95,  980.2);

-- Vložení herních session — přiřazení přes username (bez závislosti na konkrétním id)
INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 25, 2, 120, 60, 320.5 FROM user WHERE username = 'emil';

INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 30, 3, 150, 75, 410.2 FROM user WHERE username = 'emil';

INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 12, 2, 70, 30, 210.8 FROM user WHERE username = 'gragas';

INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 8, 1, 45, 18, 145.3 FROM user WHERE username = 'gragas';

INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 15, 3, 85, 35, 270.1 FROM user WHERE username = 'gragas';

INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 10, 2, 55, 22, 180.5 FROM user WHERE username = 'garen';

INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
SELECT id, 9, 1, 48, 20, 165.9 FROM user WHERE username = 'garen';

-- Vložení achievementů (přeskočí existující díky INSERT OR IGNORE)
INSERT OR IGNORE INTO achievement (name, description, icon) VALUES
    ('První krev',   'Zabij prvního nepřítele',                  '🩸'),
    ('Ostrostřelec', 'Dosáhni přesnosti nad 80 % v jedné hře',  '🎯'),
    ('Nezranitelný', 'Dokonči hru bez jediné kolize',             '🛡️');

-- Vložení vazeb uživatel–achievement (M:N) — přes username, ne hardcoded id
INSERT OR IGNORE INTO user_achievement (user_id, achievement_id)
SELECT u.id, a.id FROM user u, achievement a
WHERE u.username = 'emil' AND a.name = 'První krev';

INSERT OR IGNORE INTO user_achievement (user_id, achievement_id)
SELECT u.id, a.id FROM user u, achievement a
WHERE u.username = 'emil' AND a.name = 'Ostrostřelec';

INSERT OR IGNORE INTO user_achievement (user_id, achievement_id)
SELECT u.id, a.id FROM user u, achievement a
WHERE u.username = 'gragas' AND a.name = 'První krev';

INSERT OR IGNORE INTO user_achievement (user_id, achievement_id)
SELECT u.id, a.id FROM user u, achievement a
WHERE u.username = 'garen' AND a.name = 'První krev';

INSERT OR IGNORE INTO user_achievement (user_id, achievement_id)
SELECT u.id, a.id FROM user u, achievement a
WHERE u.username = 'garen' AND a.name = 'Nezranitelný';