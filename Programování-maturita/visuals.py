import math
import random
import pygame
from config import MenuConfig

# ===== COLOR CONSTANTS =====
class Colors:
    PURPLE = (254, 0, 246)
    GREEN = (11, 255, 1)
    WHITE = (255, 255, 255)
    RED = (254, 0, 0)
    YELLOW = (253, 254, 2)
    PLAYER_DEFAULT = (0, 255, 0)
    PLAYER_HURT = (255, 100, 100)
    ENEMY = (255, 0, 0)
    UI_BG = (40, 40, 40)
    STAMINA = (0, 180, 255)
    DAMAGE_TEXT = (255, 230, 180)
    HIT_PARTICLES = (255, 200, 80)
    EXPLOSIVE_PARTICLES = (255, 80, 0)
    DEATH_PARTICLES = (255, 80, 40)
    FPS_TEXT = (200, 200, 255)

# -------------------------
# FONT CACHE
# -------------------------
class FontCache:
    def __init__(self, font_path=None):
        self.fonts = {}
        self.font_path = font_path
        self.fallback = 'arial'

    def get(self, size):
        size = int(size)
        if size in self.fonts:
            return self.fonts[size]
        try:
            font = pygame.font.Font(self.font_path, size) if self.font_path else pygame.font.SysFont(self.fallback, size)
        except Exception:
            font = pygame.font.SysFont(self.fallback, size)
        self.fonts[size] = font
        return font

font_cache = FontCache(MenuConfig.MENU_FONT_PATH)

# -------------------------
# STARS (3 vrstvy)
# -------------------------
class Star:
    def __init__(self, w, h, color, speed, length, layer_factor):
        self.w = w
        self.h = h
        self.color = color
        self.speed = speed
        self.length = length
        self.layer_factor = layer_factor
        self.reset()

    def reset(self):
        self.x = random.uniform(0, self.w)
        self.y = random.uniform(-self.h, self.h)

    def update(self, dt, hyperspace):
        factor = 5.0 if hyperspace else 1.0
        self.y += self.speed * factor * dt
        if self.y > self.h:
            self.reset()

    def draw(self, surface, global_pulse, hyperspace):
        factor = 5.0 if hyperspace else 1.0
        length_draw = self.length * factor
        color = tuple(min(255, max(0, int(c + global_pulse))) for c in self.color)
        pygame.draw.line(surface, color, (self.x, self.y), (self.x, self.y + length_draw), 2)

# Vrstvy hvězd
stars_layers = []
layer_params = [(50, 0.5), (50, 1.0), (50, 1.5)]  # (počet hvězd, rychlost faktor)

for num, speed_factor in layer_params:
    layer = [
        Star(
            MenuConfig.MENU_SCREEN_WIDTH,
            MenuConfig.MENU_SCREEN_HEIGHT,
            random.choice(MenuConfig.MENU_STAR_COLORS),
            random.uniform(50, 200) * speed_factor,
            random.randint(5, 15),
            speed_factor
        )
        for _ in range(num)
    ]
    stars_layers.append(layer)

def update_stars(dt, hyperspace):
    for layer in stars_layers:
        for s in layer:
            s.update(dt, hyperspace)

def draw_stars(surface, hyperspace):
    global_pulse = math.sin(pygame.time.get_ticks() / 1000.0 * math.pi) * 10
    for layer in stars_layers:
        for s in layer:
            s.draw(surface, global_pulse, hyperspace)
