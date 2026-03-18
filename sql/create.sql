-- Vytvoření tabulky user (odpovídá modelu User)
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(150) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_admin BOOLEAN DEFAULT 0,
    enemies_killed INTEGER DEFAULT 0,
    player_collisions INTEGER DEFAULT 0,
    projectiles_fired INTEGER DEFAULT 0,
    projectiles_hit INTEGER DEFAULT 0,
    time_played FLOAT DEFAULT 0.0
);

-- Vytvoření tabulky game_session (odpovídá modelu GameSession)
CREATE TABLE game_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    enemies_killed INTEGER DEFAULT 0,
    player_collisions INTEGER DEFAULT 0,
    projectiles_fired INTEGER DEFAULT 0,
    projectiles_hit INTEGER DEFAULT 0,
    time_played FLOAT DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Vytvoření tabulky achievement (seznam achievementů)
CREATE TABLE achievement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255) NOT NULL,
    icon VARCHAR(10) DEFAULT '🏆'
);

-- Vazební tabulka M:N – uživatel může mít více achievementů, achievement více uživatelů
CREATE TABLE user_achievement (
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievement(id) ON DELETE CASCADE
);