"""
config.py
=========
Centrální konfigurace celé aplikace.

Všechny herní a menu konstanty jsou soustředěny na jednom místě,
aby změna chování hry nevyžadovala hledání hodnot napříč soubory.
Stačí upravit hodnotu zde a efekt se projeví v celém projektu.
"""

import pygame


# =============================================================================
# HERNÍ KONFIGURACE
# =============================================================================
class GameConfig:
    """
    Konstanty pro herní logiku a fyziku.

    Třída slouží čistě jako jmenný prostor (namespace) — nevytváří se
    její instance, konstanty se čtou přímo jako GameConfig.KONSTANTA.
    """

    # ── Rozlišení a výkon ────────────────────────────────────────────────────
    WIDTH, HEIGHT = 1920, 1080      # Rozměry herního okna v pixelech
    GROUND_LEVEL = HEIGHT * 0.8     # Y-souřadnice podlahy (80 % výšky obrazovky)
    FPS = 144                       # Cílový počet snímků za sekundu

    # ── Fyzika ───────────────────────────────────────────────────────────────
    GRAVITY = 800                   # Gravitační zrychlení hráče i nepřátel (px/s²)
    PROJECTILE_GRAVITY = 250        # Gravitace projektilů — slabší, aby střely nelétaly příliš strmě
    AIR_RESISTANCE = 0.02           # Koeficient vzdušného odporu projektilů (0–1); vyšší = rychlejší zpomalení
    SPREAD = 0.05                   # Maximální úhlový rozptyl střely v radiánech (simuluje nepřesnost)

    # ── Hráč ─────────────────────────────────────────────────────────────────
    PLAYER_RADIUS = 15              # Poloměr kolizní kružnice hráče (px)
    PLAYER_SPEED = 200              # Horizontální rychlost pohybu (px/s)
    PLAYER_HEALTH = 100             # Počáteční zdraví (nevyužito přímo — Player používá MAX)
    PLAYER_MAX_HEALTH = 100         # Maximální zdraví hráče
    PLAYER_POSITION_Y = pygame.Vector2(400, GROUND_LEVEL)  # Výchozí pozice (přepsána v Player.__init__)
    PLAYER_VELOCITY_Y = 0           # Výchozí vertikální rychlost

    # ── Létání a stamina ─────────────────────────────────────────────────────
    FLY_LIFT = 300                  # Vertikální síla při stisknutém mezerníku (px/s, záporná osa Y = nahoru)
    MAX_STAMINA = 100               # Maximální hodnota staminy
    STAMINA_USE = 40                # Spotřeba staminy za sekundu při létání
    STAMINA_REGEN = 20              # Regenerace staminy za sekundu při kontaktu se zemí
    STAMINA_BAR = 100               # Délka stamina baru v UI (px) — pro vizualizaci

    # ── Dash ─────────────────────────────────────────────────────────────────
    DASH_SPEED = 1500               # Rychlost dashe (px/s) — ~7,5× rychlejší než normální pohyb
    DASH_DURATION = 0.15            # Délka trvání jednoho dashe (s)
    DASH_COOLDOWN = 1000            # Cooldown mezi dashi (ms)
    DASH_TRAIL_LIFETIME = 0.25      # Jak dlouho (s) zůstávají body stopy za dashem viditelné
    DASH_TRAIL_LENGTH = 10          # Počet bodů tvořících vizuální stopu dashe

    # ── Projektily ───────────────────────────────────────────────────────────
    PROJECTILE_SPEED = 900          # Počáteční rychlost projektilu (px/s)
    PROJECTILE_RADIUS = 5           # Poloměr kolizní kružnice projektilu (px)
    PROJECTILE_DAMAGE = 20          # Základní poškození jednoho zásahu
    PROJECTILE_DELAY = 300          # Minimální interval mezi výstřely (ms) — brání spamu
    # Dostupné barvy projektilů; barva zároveň určuje typ efektu (viz utils.py)
    PROJECTILE_COLORS = [
        (254, 0, 246),   # Fialová  → pierce (průstřelný)
        (11, 255, 1),    # Zelená   → dot (damage over time)
        (255, 255, 255), # Bílá     → slow (zpomalení)
        (254, 0, 0),     # Červená  → explosive (výbuch)
        (253, 254, 2),   # Žlutá   → heal (léčení hráče)
    ]
    HIT_HEAL = 10                   # Počet HP obnovených při zásahu žlutým projektilem

    # ── Nepřátelé ────────────────────────────────────────────────────────────
    ENEMY_RADIUS = 18               # Poloměr kolizní kružnice nepřítele (px)
    ENEMY_SPEED = 100               # Základní rychlost pohybu nepřítele (px/s)
    ENEMY_SPAWN_INTERVAL = 2000     # Interval spawnu nového nepřítele (ms)
    ENEMY_MIN_HP = 60               # Minimální HP náhodně vygenerovaného nepřítele
    ENEMY_MAX_HP = 100              # Maximální HP náhodně vygenerovaného nepřítele

    # ── Částicové efekty ─────────────────────────────────────────────────────
    PARTICLE_COUNT = 12             # Výchozí počet částic při výbuchu/zásahu
    PARTICLE_LIFETIME = 0.5         # Životnost jedné částice (s)
    PARTICLE_SPEED = 200            # Maximální rychlost částice (px/s)

    # ── Vizuální efekty ──────────────────────────────────────────────────────
    VIGNETTE_DECAY = 120            # Rychlost mizení vignette efektu při zásahu (px/s)
    HURT_FLASH_TIME = 0.15          # Jak dlouho (s) bliká nepřítel po zásahu

    # ── Efekty projektilů ────────────────────────────────────────────────────
    SLOW_DURATION = 1.5             # Délka trvání efektu zpomalení (s)
    SLOW_FACTOR = 0.5               # Multiplikátor rychlosti při zpomalení (0.5 = 50 % rychlosti)
    DOT_DURATION = 2.0              # Délka trvání damage over time efektu (s)
    DOT_DAMAGE_FACTOR = 0.25        # Poškození DoT za sekundu jako násobek základního dmg projektilu


# =============================================================================
# MENU KONFIGURACE
# =============================================================================
class MenuConfig:
    """
    Konstanty pro menu, intro obrazovku a hvězdné efekty.

    Oddělené od GameConfig, protože menu běží nezávisle na herní logice
    a má vlastní smyčku i FPS nastavení.
    """

    MENU_FPS = 144                  # FPS menu smyčky
    MENU_NUM_STARS = 150            # Celkový počet hvězd na pozadí (rozděleny do 3 vrstev)
    MENU_HYPERSPACE_DURATION = 1.0  # Délka hyperspace animace při přechodu z Intra do Menu (s)

    # Barvy hvězd — shodné s barvami projektilů pro vizuální konzistenci hry
    MENU_STAR_COLORS = [
        (254, 0, 246),   # Fialová
        (11, 255, 1),    # Zelená
        (255, 255, 255), # Bílá
        (254, 0, 0),     # Červená
        (253, 254, 2),   # Žlutá
    ]

    MENU_SCREEN_WIDTH = 1920        # Šířka menu obrazovky (px)
    MENU_SCREEN_HEIGHT = 1080       # Výška menu obrazovky (px)

    # Cesta k vlastnímu fontu Orbitron — sci-fi styl odpovídající vesmírnému tématu hry
    MENU_FONT_PATH = "Assets/font/Orbitron/static/Orbitron-Regular.ttf"