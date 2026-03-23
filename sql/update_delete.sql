-- ============================================================
-- UPDATE a DELETE skripty pro databázi Projectile Combat
-- ============================================================


-- ============================================================
-- UPDATE
-- ============================================================

-- 1. Aktualizace kumulativních statistik uživatele po nové hře
UPDATE user
SET 
    enemies_killed     = enemies_killed + 10,
    projectiles_fired  = projectiles_fired + 50,
    projectiles_hit    = projectiles_hit + 30,
    time_played        = time_played + 300.0
WHERE id = 1;

-- 2. Povýšení uživatele na admina
UPDATE user
SET is_admin = 1
WHERE username = 'emil';

-- 3. Změna hesla uživatele (v praxi se hash generuje přes bcrypt v Pythonu)
UPDATE user
SET password = '$2b$12$novy_hash_hesla'
WHERE email = 'gragas@example.com';

-- 4. Oprava chybně zadaného počtu zabitých nepřátel v konkrétní session
UPDATE game_session
SET enemies_killed = 20
WHERE id = 3;

-- 5. Hromadné vynulování statistik všech uživatelů (reset sezóny)
UPDATE user
SET 
    enemies_killed    = 0,
    player_collisions = 0,
    projectiles_fired = 0,
    projectiles_hit   = 0,
    time_played       = 0.0;


-- ============================================================
-- DELETE
-- ============================================================

-- 6. Smazání konkrétní herní session (testovací / chybný záznam)
DELETE FROM game_session
WHERE id = 1;

-- 7. Smazání všech session kratších než 5 sekund (neplatné záznamy)
DELETE FROM game_session
WHERE time_played < 5.0;

-- 8. Odebrání achievementu konkrétnímu uživateli
DELETE FROM user_achievement
WHERE user_id = 2 AND achievement_id = 1;

-- 9. Smazání uživatele – díky ON DELETE CASCADE se automaticky smažou
--    i jeho game_session a user_achievement záznamy
DELETE FROM user
WHERE username = 'garen';

-- 10. Odstranění duplicitních herních session
--     Pokud byl insert.sql spuštěn vícekrát, vzniknou duplicitní záznamy
--     v game_session (tabulka nemá UNIQUE constraint).
--     Tento dotaz ponechá vždy jen první (nejnižší id) z každé skupiny duplicit.
DELETE FROM game_session
WHERE id NOT IN (
    SELECT MIN(id)
    FROM game_session
    GROUP BY user_id, enemies_killed, player_collisions,
             projectiles_fired, projectiles_hit, time_played
);