-- 1. Všechny herní session se jmény uživatelů (JOIN)
SELECT 
    u.username,
    gs.timestamp,
    gs.enemies_killed,
    gs.player_collisions,
    gs.projectiles_fired,
    gs.projectiles_hit,
    (gs.projectiles_hit * 1.0 / NULLIF(gs.projectiles_fired, 0)) * 100 AS accuracy,
    gs.time_played
FROM game_session gs
JOIN user u ON gs.user_id = u.id
ORDER BY gs.timestamp DESC;

-- 2. Nejlepší hráči podle celkového počtu zabitých nepřátel (seskupení, agregace)
SELECT 
    u.username,
    SUM(gs.enemies_killed) AS total_kills,
    AVG(gs.enemies_killed) AS avg_kills_per_game,
    COUNT(gs.id) AS games_played
FROM user u
JOIN game_session gs ON u.id = gs.user_id
GROUP BY u.id
ORDER BY total_kills DESC;

-- 3. Hry s přesností vyšší než 50 % (filtrování)
SELECT 
    u.username,
    gs.timestamp,
    (gs.projectiles_hit * 1.0 / NULLIF(gs.projectiles_fired, 0)) * 100 AS accuracy
FROM game_session gs
JOIN user u ON gs.user_id = u.id
WHERE gs.projectiles_fired > 0 
  AND (gs.projectiles_hit * 1.0 / gs.projectiles_fired) > 0.5
ORDER BY accuracy DESC;

-- 4. Průměrná délka hry pro každého uživatele (seskupení)
SELECT 
    u.username,
    AVG(gs.time_played) AS avg_time,
    MAX(gs.time_played) AS max_time
FROM user u
JOIN game_session gs ON u.id = gs.user_id
GROUP BY u.id
ORDER BY avg_time DESC;

-- 5. Uživatelé, kteří nikdy nehráli (LEFT JOIN a filtrování NULL)
SELECT 
    u.username,
    u.email
FROM user u
LEFT JOIN game_session gs ON u.id = gs.user_id
WHERE gs.id IS NULL;
-- 6. Achievementy každého uživatele (M:N JOIN přes vazební tabulku)
SELECT 
    u.username,
    a.name AS achievement,
    a.description,
    a.icon,
    ua.unlocked_at
FROM user_achievement ua
JOIN user u ON ua.user_id = u.id
JOIN achievement a ON ua.achievement_id = a.id
ORDER BY ua.unlocked_at DESC;

-- 7. Počet odemčených achievementů pro každého uživatele (agregace přes M:N)
SELECT 
    u.username,
    COUNT(ua.achievement_id) AS achievements_unlocked
FROM user u
LEFT JOIN user_achievement ua ON u.id = ua.user_id
GROUP BY u.id
ORDER BY achievements_unlocked DESC;

-- UPDATE: Aktualizace celkových statistik uživatele po nové hře
UPDATE user
SET enemies_killed = enemies_killed + 10,
    projectiles_fired = projectiles_fired + 50,
    projectiles_hit = projectiles_hit + 30,
    time_played = time_played + 300.0
WHERE id = 1;

-- DELETE: Smazání konkrétní herní session (např. testovací záznam)
DELETE FROM game_session
WHERE id = 1;

-- DELETE CASCADE ukázka: Smazání uživatele smaže i jeho session a achievementy
-- DELETE FROM user WHERE id = 3;