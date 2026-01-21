import pygame
# ===== GAME CONFIGURATION =====
class GameConfig:
    WIDTH, HEIGHT = 1920, 1080
    GROUND_LEVEL = HEIGHT * 0.8
    FPS = 144  # ZMĚNA: 144 FPS místo 60
    
    # Physics
    GRAVITY = 800
    PROJECTILE_GRAVITY = 250
    AIR_RESISTANCE = 0.02
    SPREAD = 0.05
    
    # Player
    PLAYER_RADIUS = 15
    PLAYER_SPEED = 200
    PLAYER_MAX_HEALTH = 100
    PLAYER_POSITION_Y = pygame.Vector2(400, GROUND_LEVEL)
    PLAYER_VELOCITY_Y = 0
    
    # Flight
    FLY_LIFT = 300
    MAX_STAMINA = 100
    STAMINA_USE = 40
    STAMINA_REGEN = 20
    STAMINA_BAR = 100
    
    # Dash
    DASH_SPEED = 1500
    DASH_DURATION = 0.15
    DASH_COOLDOWN = 1000
    DASH_TRAIL_LIFETIME = 0.25
    DASH_TRAIL_LENGTH = 10
    
    # Projectiles
    PROJECTILE_SPEED = 900
    PROJECTILE_RADIUS = 5
    PROJECTILE_DAMAGE = 20
    PROJECTILE_DELAY = 300
    PROJECTILE_COLORS = [(254,0,246), (11,255,1), (255,255,255), (254,0,0), (253,254,2)]
    HIT_HEAL = 10

    
    # Enemies
    ENEMY_RADIUS = 18
    ENEMY_SPEED = 100
    ENEMY_SPAWN_INTERVAL = 2000
    ENEMY_MIN_HP = 60
    ENEMY_MAX_HP = 100

    # Particle Effects
    PARTICLE_COUNT = 12
    PARTICLE_LIFETIME = 0.5
    PARTICLE_SPEED = 200
    
    # Effects
    VIGNETTE_DECAY = 120
    HURT_FLASH_TIME = 0.15
    SLOW_DURATION = 1.5
    SLOW_FACTOR = 0.5
    DOT_DURATION = 2.0
    DOT_DAMAGE_FACTOR = 0.25

# =====MENU CONFIGURATION=====
class MenuConfig:
    MENU_FPS = 144
    MENU_NUM_STARS = 150
    MENU_HYPERSPACE_DURATION = 1.0
    MENU_STAR_COLORS = [(254,0,246), (11,255,1), (255,255,255), (254,0,0), (253,254,2)]
    MENU_SCREEN_WIDTH = 1920
    MENU_SCREEN_HEIGHT = 1080
    MENU_FONT_PATH = "Assets/font/Orbitron/static/Orbitron-Regular.ttf"
