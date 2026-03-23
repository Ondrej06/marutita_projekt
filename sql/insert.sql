-- ============================================================
-- Vyčištění předchozích testovacích dat (idempotentní spuštění)
-- Smaže jen testovací uživatele — admin a reálné hráče ponechá.
-- CASCADE automaticky smaže i jejich game_session a user_achievement záznamy.
-- ============================================================
DELETE FROM user WHERE username IN ('emil', 'gragas', 'garen');

-- Vložení uživatelů
INSERT INTO user (username, email, password, is_admin, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
VALUES 
    ('emil', 'emil@example.com', '$2b$12$hashed_password_here', 0, 150, 12, 800, 450, 3600.5),
    ('gragas', 'gragas@example.com', '$2b$12$hashed_password_here', 0, 42, 8, 320, 180, 1250.0),
    ('garen', 'garen@example.com', '$2b$12$hashed_password_here', 0, 27, 5, 210, 95, 980.2);

-- Vložení herních session (každý uživatel alespoň 2)
INSERT INTO game_session (user_id, enemies_killed, player_collisions, projectiles_fired, projectiles_hit, time_played)
VALUES
    (1, 25, 2, 120, 60, 320.5),  -- emil, hra 1
    (1, 30, 3, 150, 75, 410.2),  -- emil, hra 2
    (2, 12, 2, 70, 30, 210.8),   -- gragas, hra 1
    (2, 8, 1, 45, 18, 145.3),    -- gragas, hra 2
    (2, 15, 3, 85, 35, 270.1),   -- gragas, hra 3
    (3, 10, 2, 55, 22, 180.5),   -- garen, hra 1
    (3, 9, 1, 48, 20, 165.9);    -- garen, hra 2

-- Vložení achievementů
INSERT INTO achievement (name, description, icon) VALUES
    ('První krev',      'Zabij prvního nepřítele',              '🩸'),
    ('Ostrostřelec',    'Dosáhni přesnosti nad 80 % v jedné hře', '🎯'),
    ('Nezranitelný',    'Dokonči hru bez jediné kolize',         '🛡️');

-- Vložení vazeb uživatel–achievement (M:N)
INSERT INTO user_achievement (user_id, achievement_id) VALUES
    (1, 1),  -- emil: První krev
    (1, 2),  -- emil: Ostrostřelec
    (2, 1),  -- gragas: První krev
    (3, 1),  -- garen: První krev
    (3, 3);  -- garen: Nezranitelný