"""
visuals.py
==========
Vizuální konstanty, cache fontů a hvězdné pozadí menu.

Modul sdružuje tři nezávislé části:
  1. Colors  — centrální paleta barev pro celou hru
  2. FontCache — LRU-like cache fontu, zamezuje opakovanému načítání
  3. Star systém — 3vrstvé parallax hvězdné pozadí s hyperspace efektem
"""

import math
import random
import pygame
from config import MenuConfig


# =============================================================================
# BAREVNÁ PALETA
# =============================================================================
class Colors:
    """
    Centrální paleta RGB barev používaných v celém projektu.

    Definováním barev na jednom místě zajišťujeme vizuální konzistenci.
    Při změně barvy stačí upravit hodnotu zde — efekt se projeví všude.
    """
    # Barvy projektilů (shodné s GameConfig.PROJECTILE_COLORS — pro přiřazení efektů)
    PURPLE = (254, 0, 246)    # Fialová  → pierce efekt
    GREEN  = (11, 255, 1)     # Zelená   → dot (damage over time) efekt
    WHITE  = (255, 255, 255)  # Bílá     → slow (zpomalení) efekt
    RED    = (254, 0, 0)      # Červená  → explosive (výbuch) efekt
    YELLOW = (253, 254, 2)    # Žlutá   → heal (léčení) efekt

    # Barvy herních objektů
    PLAYER_DEFAULT = (0, 255, 0)    # Normální barva hráče (zelená)
    PLAYER_HURT    = (255, 100, 100) # Barva hráče při zásahu (světle červená) — zatím rezerva
    ENEMY          = (255, 0, 0)    # Základní barva nepřítele (červená)

    # UI prvky
    UI_BG   = (40, 40, 40)     # Pozadí health/stamina barů
    STAMINA = (0, 180, 255)    # Modrá pro stamina bar

    # Herní efekty
    DAMAGE_TEXT       = (255, 230, 180)  # Plovoucí text poškození (světle oranžová)
    HIT_PARTICLES     = (255, 200, 80)   # Částice při zásahu nepřítele
    EXPLOSIVE_PARTICLES = (255, 80, 0)   # Částice výbuchu (rezerva)
    DEATH_PARTICLES   = (255, 80, 40)    # Částice při smrti nepřítele

    # Ostatní
    FPS_TEXT = (200, 200, 255)  # Barva FPS čítače (světle modrofialová)


# =============================================================================
# CACHE FONTŮ
# =============================================================================
class FontCache:
    """
    Cache pro pygame fonty různých velikostí.

    Pygame vytváří nový font objekt pro každou velikost. Opakované
    volání pygame.font.Font() při každém snímku by bylo výkonnostně
    nákladné. FontCache udrží jednu instanci fontu pro každou použitou
    velikost a vrátí ji při opakovaném dotazu.

    Attributes:
        fonts (dict): Slovník {velikost: pygame.font.Font}.
        font_path (str | None): Cesta k TTF souboru vlastního fontu.
        fallback (str): Název systémového fontu jako záloha.
    """

    def __init__(self, font_path: str = None):
        """
        Inicializuje cache.

        Args:
            font_path: Cesta k TTF souboru vlastního fontu.
                       Pokud None nebo soubor neexistuje, použije se fallback.
        """
        self.fonts = {}
        self.font_path = font_path
        self.fallback = 'arial'

    def get(self, size: int) -> pygame.font.Font:
        """
        Vrátí font zadané velikosti. Pokud ještě není v cache, vytvoří ho.

        Args:
            size: Velikost fontu v bodech.

        Returns:
            pygame.font.Font: Instance fontu připravená k vykreslování.
        """
        size = int(size)  # Zajistí celočíselnou velikost (lerp vrací float)
        if size in self.fonts:
            return self.fonts[size]  # Cache hit — vrátíme existující instanci

        # Cache miss — vytvoříme nový font a uložíme do cache
        try:
            font = (
                pygame.font.Font(self.font_path, size)
                if self.font_path
                else pygame.font.SysFont(self.fallback, size)
            )
        except Exception:
            # Vlastní font se nepodařilo načíst (chybí soubor) — fallback
            font = pygame.font.SysFont(self.fallback, size)

        self.fonts[size] = font
        return font


# Globální instance cache — používají ji všechny moduly přes `from visuals import font_cache`
font_cache = FontCache(MenuConfig.MENU_FONT_PATH)


# =============================================================================
# HVĚZDNÉ POZADÍ (parallax, 3 vrstvy)
# =============================================================================
class Star:
    """
    Jedna hvězda v parallax hvězdném pozadí.

    Hvězdy se pohybují shora dolů (simulace pohledu do vesmíru ze shora).
    Různé rychlosti v různých vrstvách vytvářejí hloubkový (parallax) efekt.
    Při hyperspace módu se rychlost znásobí 5×.

    Attributes:
        x, y (float): Aktuální pozice hvězdy.
        speed (float): Rychlost pohybu dolů (px/s).
        length (int): Délka čáry hvězdy (px) — delší = vypadá blíž.
        color (tuple): RGB barva hvězdy.
    """

    def __init__(self, w: int, h: int, color: tuple, speed: float,
                 length: int, layer_factor: float):
        """
        Args:
            w, h: Rozměry obrazovky pro výpočet hranic.
            color: RGB barva hvězdy.
            speed: Základní rychlost pohybu (px/s).
            length: Délka vizuální čáry hvězdy (px).
            layer_factor: Faktor vrstvy (pomalejší vrstvy = vzdálenější hvězdy).
        """
        self.w = w
        self.h = h
        self.color = color
        self.speed = speed
        self.length = length
        self.layer_factor = layer_factor
        self.reset()

    def reset(self):
        """Přemístí hvězdu na náhodnou pozici na horní části obrazovky."""
        self.x = random.uniform(0, self.w)
        self.y = random.uniform(-self.h, self.h)  # Záporné Y = nad obrazovkou

    def update(self, dt: float, hyperspace: bool):
        """
        Posune hvězdu dolů. V hyperspace režimu 5× rychleji.

        Args:
            dt: Delta time v sekundách.
            hyperspace: True = aktivní warp/hyperspace animace.
        """
        factor = 5.0 if hyperspace else 1.0
        self.y += self.speed * factor * dt

        # Hvězda zmizela pod obrazovkou — přemístíme ji zpět nahoru
        if self.y > self.h:
            self.reset()

    def draw(self, surface: pygame.Surface, global_pulse: float, hyperspace: bool):
        """
        Vykreslí hvězdu jako svislou čáru s pulzující jasností.

        Args:
            surface: Cílový pygame povrch.
            global_pulse: Globální sinusová hodnota (-15 až +15) pro blikání.
            hyperspace: V hyperspace režimu se délka čáry zvětší 5×.
        """
        factor = 5.0 if hyperspace else 1.0
        length_draw = self.length * factor

        # Přidáme pulz k barvě (clamp na 0–255 zabrání přetečení)
        color = tuple(min(255, max(0, int(c + global_pulse))) for c in self.color)
        pygame.draw.line(
            surface, color,
            (self.x, self.y),
            (self.x, self.y + length_draw),
            2  # Tloušťka čáry v pixelech
        )


# =============================================================================
# INICIALIZACE HVĚZDNÝCH VRSTEV
# =============================================================================
# 3 vrstvy s různou hustotou a rychlostí — parallax hloubkový efekt:
#   Vrstva 1 (pomalá)  → vzdálené hvězdy, jemné pohyby
#   Vrstva 2 (střední) → střední vzdálenost
#   Vrstva 3 (rychlá)  → blízké hvězdy, výrazný pohyb
stars_layers = []
layer_params = [(50, 0.5), (50, 1.0), (50, 1.5)]  # (počet hvězd, rychlostní faktor)

for num, speed_factor in layer_params:
    layer = [
        Star(
            MenuConfig.MENU_SCREEN_WIDTH,
            MenuConfig.MENU_SCREEN_HEIGHT,
            random.choice(MenuConfig.MENU_STAR_COLORS),
            random.uniform(50, 200) * speed_factor,  # Náhodná rychlost * faktor vrstvy
            random.randint(5, 15),                    # Náhodná délka čáry
            speed_factor
        )
        for _ in range(num)
    ]
    stars_layers.append(layer)


def update_stars(dt: float, hyperspace: bool) -> None:
    """
    Aktualizuje pozice všech hvězd ve všech vrstvách.

    Args:
        dt: Delta time v sekundách od posledního snímku.
        hyperspace: True = zvýšit rychlost pro hyperspace animaci.
    """
    for layer in stars_layers:
        for s in layer:
            s.update(dt, hyperspace)


def draw_stars(surface: pygame.Surface, hyperspace: bool) -> None:
    """
    Vykreslí všechny hvězdy na zadaný povrch.

    Globální pulz (sinusová funkce) způsobuje synchronizované mírné
    blikání všech hvězd — simuluje třpytění vesmírné oblohy.

    Args:
        surface: Cílový pygame povrch (hlavní okno).
        hyperspace: True = hyperspace vizuální efekty.
    """
    # Sinusový pulz -10 až +10 synchronizovaný s herním časem
    global_pulse = math.sin(pygame.time.get_ticks() / 1000.0 * math.pi) * 10

    for layer in stars_layers:
        for s in layer:
            s.draw(surface, global_pulse, hyperspace)