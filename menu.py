"""
menu.py
=======
Hlavní vstupní bod aplikace — spouštěcí skript menu a hry.

Tento soubor inicializuje Pygame, načte konfiguraci z config.json,
synchronizuje rozlišení do GameConfig a MenuConfig, vytvoří
StateManager se všemi stavy a spustí hlavní smyčku.

Spuštění:
    python menu.py

Architektura:
    StateManager drží aktuální stav (Intro, MainMenu, Playing atd.)
    a deleguje události, update a render na jeho implementaci.
    Pozadí (hvězdy, meteory) se vykresluje vždy — nezávisle na stavu.

    Rozlišení okna se načítá z config.json a přepisuje výchozí hodnoty
    GameConfig.WIDTH/HEIGHT i MenuConfig.MENU_SCREEN_WIDTH/HEIGHT,
    takže všechny moduly pracují s aktuálně nastaveným rozlišením.
"""

import pygame
import random
from config import GameConfig, MenuConfig
from visuals import update_stars, draw_stars
from states import GameState
from states_menu import IntroState, LoginState, MainMenuState, SettingsState, GraphicsState
from states_game import PlayingState
from settings import load_config

# ── Načtení konfigurace a synchronizace rozlišení ────────────────────────────
config = load_config()
width, height = config["resolution"]

# Přepsání GameConfig na rozlišení uložené v config.json
# (uživatel mohl změnit rozlišení v Settings → Graphics)
GameConfig.WIDTH = width
GameConfig.HEIGHT = height

# Poznámka: pygame.display.set_mode() se volá až uvnitř main() po pygame.init()


# =============================================================================
# SYSTÉM METEORŮ
# =============================================================================
class MeteorSystem:
    """
    Generuje a vykresluje náhodné meteory padající přes menu obrazovku.

    Meteory jsou jednoduché svislé čáry pohybující se shora dolů.
    Přidávají atmosféru vesmírného prostředí menu.

    Attributes:
        meteors (list): Seznam aktivních meteorů jako slovníky {x, y, length, speed}.
    """

    def __init__(self, width: int, height: int):
        """
        Args:
            width, height: Rozměry obrazovky pro generování a kontrolu hranic.
        """
        self.width = width
        self.height = height
        self.meteors = []

    def update(self, dt: float) -> None:
        """
        Posunuje meteory dolů a generuje nové s náhodnou pravděpodobností.

        Nový meteor vznikne s pravděpodobností 1 % za snímek,
        ale maximálně 3 meteory mohou existovat současně.

        Args:
            dt: Delta time v sekundách.
        """
        # Generuj nový meteor s 1% pravděpodobností (max 3 najednou)
        if random.random() < 0.01 and len(self.meteors) < 3:
            self.meteors.append({
                "x":      random.randint(0, self.width),
                "y":      0,                               # Začíná na vrcholu obrazovky
                "length": random.randint(10, 30),          # Délka čáry
                "speed":  random.uniform(500, 800),        # Rychlost pádu (px/s)
            })

        # Posuň každý meteor dolů; mrtvé (pod obrazovkou) odstraň
        for m in self.meteors[:]:
            m["y"] += m["speed"] * dt
            if m["y"] > self.height:
                self.meteors.remove(m)

    def draw(self, surface: pygame.Surface) -> None:
        """
        Vykreslí každý meteor jako bílou svislou čáru.

        Args:
            surface: Cílový pygame povrch.
        """
        for m in self.meteors:
            pygame.draw.line(
                surface,
                (255, 255, 255),
                (m["x"], m["y"]),
                (m["x"], m["y"] + m["length"]),
                2   # Tloušťka čáry
            )


# =============================================================================
# STATE MANAGER
# =============================================================================
class StateManager:
    """
    Správce herních stavů — implementace vzoru State Machine.

    Drží registr všech dostupných stavů a referenci na aktuální stav.
    Při přechodu volá exit() na starém a enter() na novém stavu.
    Deleguje události, update a render na aktuální stav.

    Attributes:
        states (dict): Slovník {GameState enum → BaseState instance}.
        current (BaseState | None): Aktuálně aktivní stav.
        running (bool): False = hlavní smyčka se ukončí.
        screen (pygame.Surface): Reference na herní okno (nastaví se po init).
        user_data (dict | None): Data přihlášeného uživatele z Flask API.
                                 None = nikdo není přihlášen.
    """

    def __init__(self):
        self.states = {}
        self.current = None
        self.running = True
        # Inicializováno jako None — přihlášení nastaví hodnotu v LoginState.
        # Formát po přihlášení: { 'user': { 'id': int, 'username': str, 'is_admin': bool } }
        # Díky inicializaci zde není potřeba hasattr() kontrola nikde v projektu.
        self.user_data = None

    def register(self, key: GameState, state_obj) -> None:
        """
        Registruje stav pod daným klíčem.

        Args:
            key: GameState enum hodnota (např. GameState.MAIN_MENU).
            state_obj: Instance třídy dědící z BaseState.
        """
        self.states[key] = state_obj

    def change_state(self, key: GameState, payload=None) -> None:
        """
        Přepne na stav identifikovaný klíčem.

        Volá exit() na aktuálním stavu (uložení dat, cleanup)
        a enter() na novém stavu (inicializace). payload umožňuje
        předat data novému stavu (zatím nevyužito).

        Args:
            key: Klíč cílového stavu.
            payload: Volitelná data předaná novému stavu přes enter().
        """
        if self.current:
            self.current.exit()

        self.current = self.states.get(key)

        if self.current:
            self.current.enter(payload)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Předá pygame událost aktuálnímu stavu."""
        if self.current:
            self.current.handle_event(event)

    def update(self, dt: float) -> None:
        """Aktualizuje aktuální stav o delta time."""
        if self.current:
            self.current.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        """Vykreslí aktuální stav na zadaný povrch."""
        if self.current:
            self.current.render(surface)


# =============================================================================
# VESMÍRNÉ POZADÍ MENU
# =============================================================================
def create_space_background(width: int, height: int) -> pygame.Surface:
    """
    Vytvoří statické vesmírné pozadí pro menu obrazovku.

    Skládá se ze dvou vrstev:
      1. Gradientní přechod černá (nahoře) → tmavě fialová (dole).
      2. Náhodné mlhoviny jako průhledné barevné kruhy (nebulae).

    Pozadí se vytvoří jednou při startu — není potřeba ho generovat každý snímek.

    Args:
        width, height: Rozměry výsledného povrchu (px).

    Returns:
        pygame.Surface: Hotové pozadí připravené k blit().
    """
    surface = pygame.Surface((width, height))

    top_color    = (0, 0, 0)       # Horní okraj: černá
    bottom_color = (20, 0, 40)     # Dolní okraj: tmavě fialová

    # Gradient: každý řádek má jinou barvu interpolovanou mezi top a bottom
    for y in range(height):
        ratio = y / height  # 0.0 nahoře, 1.0 dole
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    # Mlhoviny: 5 náhodně umístěných průhledných kruhů
    nebula_colors = [(100, 0, 150), (50, 0, 100), (20, 10, 60)]
    for _ in range(5):
        pos    = (random.randint(0, width), random.randint(0, height))
        radius = random.randint(150, 400)
        color  = random.choice(nebula_colors)
        alpha  = random.randint(30, 80)   # Nízká alpha = jemný efekt

        # Povrch s alfa kanálem pro průhlednou mlhovinu
        nebula = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(nebula, (*color, alpha), (radius, radius), radius)
        surface.blit(nebula, (pos[0] - radius, pos[1] - radius))

    return surface


# =============================================================================
# HLAVNÍ FUNKCE
# =============================================================================
def main() -> None:
    """
    Inicializuje celou aplikaci a spustí hlavní herní smyčku.

    Postup:
      1. Inicializace Pygame.
      2. Synchronizace MenuConfig s rozlišením z config.json.
      3. Vytvoření okna a hodin.
      4. Generování statického pozadí a systému meteorů.
      5. Vytvoření StateManageru, registrace všech stavů.
      6. Spuštění stavu INTRO.
      7. Hlavní smyčka: events → update → render → flip.
    """
    pygame.init()

    # Rozměry okna z config.json (GameConfig byl přepsán při startu menu.py)
    width  = GameConfig.WIDTH
    height = GameConfig.HEIGHT

    # Synchronizace MenuConfig — ostatní moduly čtou MenuConfig při importu,
    # toto zajistí konzistenci pro veškeré dynamické dotazy
    MenuConfig.MENU_SCREEN_WIDTH  = width
    MenuConfig.MENU_SCREEN_HEIGHT = height
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Bubble Shooter")
    clock = pygame.time.Clock()

    # Statické pozadí (gradient + mlhoviny) — generuje se jednou
    background = create_space_background(width, height)
    meteors = MeteorSystem(width, height)

    # ── Inicializace StateManageru ────────────────────────────────────────────
    manager = StateManager()
    manager.screen = screen

    # Vytvoření instancí všech stavů
    intro     = IntroState(manager)
    main_menu = MainMenuState(manager)
    settings  = SettingsState(manager)
    playing   = PlayingState(manager)
    login     = LoginState(manager)
    graphics  = GraphicsState(manager)

    # Registrace stavů pod enum klíči
    manager.register(GameState.INTRO,      intro)
    manager.register(GameState.MAIN_MENU,  main_menu)
    manager.register(GameState.SETTINGS,   settings)
    manager.register(GameState.PLAYING,    playing)
    manager.register(GameState.LOGIN,      login)
    manager.register(GameState.GRAPHICS,   graphics)

    # Spuštění úvodní animace
    manager.change_state(GameState.INTRO)

    # ── Hlavní smyčka ─────────────────────────────────────────────────────────
    while manager.running:
        # Delta time: čas od posledního snímku v sekundách
        dt = clock.tick(MenuConfig.MENU_FPS) / 1000.0

        # ── Zpracování událostí ───────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                manager.running = False
                continue

            # Deleguj událost na aktuální stav
            manager.handle_event(event)

            # Speciální případ: klávesa v IntroState spustí hyperspace animaci
            if (event.type == pygame.KEYDOWN
                    and manager.current is intro
                    and not intro.hyperspace):
                intro.hyperspace = True
                intro.hyperspace_timer = 0.0

        # Detekce hyperspace pro správné vykreslení hvězd
        hyperspace = (
            manager.current is intro
            and getattr(intro, "hyperspace", False)
        )

        # ── Update ────────────────────────────────────────────────────────────
        meteors.update(dt)
        update_stars(dt, hyperspace)   # Hvězdy z visuals.py (globální instance)
        manager.update(dt)

        # ── Render ────────────────────────────────────────────────────────────
        screen.blit(background, (0, 0))   # Statické pozadí jako první vrstva
        meteors.draw(screen)              # Animované meteory
        draw_stars(screen, hyperspace)    # Parallax hvězdy
        manager.render(screen)            # Aktuální stav (menu, hra, login...)

        pygame.display.flip()             # Zobraz vykreslený snímek

    pygame.quit()


if __name__ == "__main__":
    main()