"""
utils.py
========
Pomocné třídy a funkce používané napříč celým projektem.

Modul obsahuje tři části:
  1. HelperFunctions — statické metody pro herní logiku (spawn, kolize, částice)
  2. GameState       — konstanty stavů pro render.py (pauza, game over)
  3. InputBox        — textové vstupní pole pro pygame UI (login formulář)

Funkce calculate_hit_accuracy je dostupná jak jako metoda HelperFunctions,
tak jako samostatná funkce (pro import v render.py).
"""

import pygame
import math
import random
from config import GameConfig
from visuals import Colors
from projectiles import Projectile
from enemy import Enemy


# =============================================================================
# POMOCNÉ HERNÍ FUNKCE
# =============================================================================
class HelperFunctions:
    """
    Kolekce statických pomocných metod pro herní logiku.

    Všechny metody jsou @staticmethod — nevyžadují instanci třídy.
    Sdruženy do třídy pouze pro organizaci jmenného prostoru.
    """

    @staticmethod
    def check_collision(circle1: pygame.Vector2, circle2: pygame.Vector2,
                        r1: float, r2: float) -> bool:
        """
        Detekuje kolizi dvou kruhových objektů.

        Kolize nastane, pokud vzdálenost středů je menší než součet poloměrů.
        Tato metoda je rychlá a vhodná pro real-time herní smyčku.

        Args:
            circle1: Střed prvního kruhu (pygame.Vector2).
            circle2: Střed druhého kruhu (pygame.Vector2).
            r1: Poloměr prvního kruhu (px).
            r2: Poloměr druhého kruhu (px).

        Returns:
            True pokud se kruhy překrývají, jinak False.
        """
        return circle1.distance_to(circle2) < (r1 + r2)

    @staticmethod
    def spawn_hit_particles(pos: pygame.Vector2, color: tuple,
                            count: int = 12, speed: float = 200,
                            lifetime: float = 0.5) -> list:
        """
        Vytvoří seznam částic explodujících z dané pozice.

        Každá částice má náhodný směr (360°) a náhodnou rychlost
        v rozsahu 30–100 % zadané maximální rychlosti.
        Částice jsou slovníky zpracovávané přímo v herní smyčce.

        Args:
            pos: Pozice středu výbuchu (obvykle poloha zasaženého nepřítele).
            color: RGB barva částic.
            count: Počet vygenerovaných částic.
            speed: Maximální rychlost částice (px/s).
            lifetime: Životnost každé částice (s).

        Returns:
            list: Seznam slovníků s klíči 'pos','vel','life','max_life','color','radius'.
        """
        new_particles = []
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)  # Náhodný směr 0–360°
            # Náhodná rychlost — dolní hranice 30 % zabrání shlukování u středu
            vel = pygame.Vector2(
                math.cos(angle), math.sin(angle)
            ) * random.uniform(speed * 0.3, speed)

            new_particles.append({
                'pos':      pos.copy(),         # Kopie pozice (ne reference)
                'vel':      vel,
                'life':     lifetime,           # Aktuální zbývající životnost
                'max_life': lifetime,           # Původní životnost pro výpočet alpha
                'color':    color,
                'radius':   random.uniform(2, 5)  # Náhodná velikost pro rozmanitost
            })
        return new_particles

    @staticmethod
    def spawn_damage_text(pos: pygame.Vector2, text,
                          color: tuple = Colors.DAMAGE_TEXT,
                          life: float = 0.7) -> dict:
        """
        Vytvoří plovoucí text zobrazující způsobené poškození.

        Text stoupá pomalu nahoru a postupně mizí (alpha klesá s life).
        Zpracovává se v herní smyčce stejně jako částice.

        Args:
            pos: Počáteční pozice textu (obvykle nad zasaženým nepřítelem).
            text: Hodnota k zobrazení (typicky číslo poškození).
            color: RGB barva textu.
            life: Životnost textu v sekundách.

        Returns:
            dict: Slovník s klíči 'pos','text','life','max_life','vel'.
        """
        return {
            'pos':      pos.copy(),
            'text':     str(text),
            'life':     life,
            'max_life': life,
            'vel':      pygame.Vector2(0, -40)  # Stoupá nahoru rychlostí 40 px/s
        }

    @staticmethod
    def spawn_enemy_improved() -> 'Enemy':
        """
        Vytvoří nového nepřítele na náhodné straně obrazovky.

        Nepřítel se spawne mimo viditelnou část (záporné/nadlimitní X),
        aby působil dojmem, že přichází z okraje obrazovky.
        HP je náhodné v rozsahu ENEMY_MIN_HP–ENEMY_MAX_HP.

        Returns:
            Enemy: Nová instance nepřítele připravená k přidání do seznamu.
        """
        side = random.choice(["left", "right"])

        # Pozice mimo obrazovku o radius px — nepřítel vstoupí hladce
        x = (-GameConfig.ENEMY_RADIUS if side == "left"
             else GameConfig.WIDTH + GameConfig.ENEMY_RADIUS)

        hp = random.randint(GameConfig.ENEMY_MIN_HP, GameConfig.ENEMY_MAX_HP)

        # Lokální import zabrání cyklické závislosti (enemy importuje z config, ne z utils)
        from enemy import Enemy
        return Enemy(x, GameConfig.GROUND_LEVEL, hp=hp)

    @staticmethod
    def spawn_projectile_instance(player_pos: pygame.Vector2,
                                  current_time: int) -> 'Projectile':
        """
        Vytvoří nový projektil namířený od hráče ke kurzoru myši.

        Postup:
          1. Zjistí aktuální pozici kurzoru.
          2. Vypočítá normalizovaný směrový vektor hráč → kurzor.
          3. Přidá náhodný rozptyl (SPREAD) simulující nepřesnost střelby.
          4. Náhodně vybere barvu — ta určuje i typ efektu (viz effect_map).

        Args:
            player_pos: Aktuální pozice hráče (střed střely při výstřelu).
            current_time: Aktuální pygame timestamp (ms) — zatím nevyužito, rezerva.

        Returns:
            Projectile: Nová instance projektilu připravená k přidání do seznamu.
        """
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        direction = mouse_pos - player_pos

        # Normalizuj směrový vektor (bez normalizace by záleželo na vzdálenosti kurzoru)
        if direction.length() > 0:
            direction = direction.normalize()

        # Přidej náhodný rotační rozptyl v rozsahu ±SPREAD radiánů
        direction = direction.rotate_rad(
            random.uniform(-GameConfig.SPREAD, GameConfig.SPREAD)
        )

        # Náhodná barva z palety — barva určuje efekt projektilu
        color = random.choice(GameConfig.PROJECTILE_COLORS)

        # Mapování barvy na typ efektu
        effect_map = {
            Colors.RED:    "explosive",  # Výbuch — poškodí okolní nepřátele
            Colors.WHITE:  "slow",       # Zpomalení nepřítele
            Colors.GREEN:  "dot",        # Damage over Time
            Colors.PURPLE: "pierce",     # Průstřelný — projde více nepřáteli
            Colors.YELLOW: "heal",       # Léčení hráče při zásahu
        }
        effect_type = effect_map.get(color, "none")

        # Lokální import zabrání cyklické závislosti
        from projectiles import Projectile
        return Projectile(
            pos=player_pos.copy(),
            vel=direction * GameConfig.PROJECTILE_SPEED,
            color=color,
            effect_type=effect_type
        )

    @staticmethod
    def calculate_accuracy(stats_dict: dict) -> float:
        """
        Vypočítá procentuální přesnost zásahů pro danou hru.

        Args:
            stats_dict: Slovník statistik s klíči 'projectiles_fired' a 'projectiles_hit'.

        Returns:
            float: Přesnost v procentech (0.0–100.0+). Při nulových výstřelech vrátí 0.0.
        """
        fired = stats_dict.get("projectiles_fired", 0)
        if fired > 0:
            return (stats_dict.get("projectiles_hit", 0) / fired) * 100
        return 0.0

    @staticmethod
    def is_off_screen(pos: pygame.Vector2, margin: int = 50) -> bool:
        """
        Zkontroluje, zda je pozice mimo hranice herní obrazovky.

        Margin poskytuje toleranční pásmo — objekt musí být margin px
        za hranicí, aby byl považován za mimo obrazovku.

        Args:
            pos: Testovaná pozice.
            margin: Tolerance v px za hranicí obrazovky.

        Returns:
            bool: True pokud je pozice mimo obrazovku + margin.
        """
        return (pos.x < -margin or pos.x > GameConfig.WIDTH + margin or
                pos.y < -margin or pos.y > GameConfig.HEIGHT + margin)

    @staticmethod
    def lerp_color(color1: tuple, color2: tuple, t: float) -> tuple:
        """
        Lineárně interpoluje mezi dvěma RGB barvami.

        Používá se pro plynulé barevné přechody (efekty blikání, zdraví).

        Args:
            color1: Výchozí RGB barva (t=0.0).
            color2: Cílová RGB barva (t=1.0).
            t: Interpolační faktor (0.0 = color1, 1.0 = color2).

        Returns:
            tuple: Interpolovaná RGB barva.
        """
        r = int(color1[0] + (color2[0] - color1[0]) * t)
        g = int(color1[1] + (color2[1] - color1[1]) * t)
        b = int(color1[2] + (color2[2] - color1[2]) * t)
        return (r, g, b)

    @staticmethod
    def format_time(seconds: float) -> str:
        """
        Formátuje čas v sekundách do čitelného řetězce MM:SS.

        Args:
            seconds: Čas v sekundách.

        Returns:
            str: Formátovaný čas, např. '02:35'.
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


# =============================================================================
# SAMOSTATNÁ FUNKCE (pro import v render.py)
# =============================================================================
def calculate_hit_accuracy(hits: int, shots: int) -> float:
    """
    Vypočítá procentuální přesnost zásahů.

    Samostatná funkce (mimo třídu) pro přímý import v render.py,
    kde by import celé třídy HelperFunctions byl zbytečný.

    Args:
        hits: Počet úspěšných zásahů.
        shots: Celkový počet výstřelů.

    Returns:
        float: Přesnost v procentech (0.0–100.0+). Při shots=0 vrátí 0.
    """
    if shots == 0:
        return 0
    return (hits / shots) * 100


# =============================================================================
# STAVY PRO RENDER.PY
# =============================================================================
class GameState:
    """
    Konstanty herních stavů pro render.py.

    Pozor: Hlavní stavy hry (enum) jsou definovány v states.py jako GameState(Enum).
    Tato třída je oddělená a slouží render.py pro rozlišení PAUSED / GAME_OVER
    při vykreslování overlay prvků.
    """
    MENU      = "menu"       # Hlavní menu (nepoužívá se v render.py)
    PLAYING   = "playing"    # Hra probíhá normálně
    PAUSED    = "paused"     # Hra je pozastavena — zobrazí se PAUSED overlay
    GAME_OVER = "game_over"  # Hráč zemřel — zobrazí se GAME OVER overlay


# =============================================================================
# VSTUPNÍ POLE PRO PYGAME
# =============================================================================
class InputBox:
    """
    Interaktivní textové vstupní pole pro pygame UI.

    Používá se v LoginState (states.py) pro zadání uživatelského jména a hesla.
    Podporuje zobrazení hesla jako hvězdiček (is_password=True).

    Attributes:
        rect (pygame.Rect): Ohraničující obdélník pole.
        color (pygame.Color): Aktuální barva rámečku (šedá = neaktivní, bílá = aktivní).
        text (str): Aktuální obsah pole.
        active (bool): True = pole je aktivní (přijímá klávesové vstupy).
        is_password (bool): True = zobrazuje hvězdičky místo znaků.
    """

    def __init__(self, x: int, y: int, w: int, h: int,
                 font: pygame.font.Font, is_password: bool = False):
        """
        Args:
            x, y: Pozice levého horního rohu pole (px).
            w, h: Šířka a výška pole (px).
            font: Pygame font pro vykreslení textu.
            is_password: True = maskuje obsah hvězdičkami.
        """
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color('gray')   # Barva neaktivního pole
        self.color_active   = pygame.Color('white')  # Barva aktivního pole
        self.color = self.color_inactive
        self.text = ""
        self.font = font
        self.active = False
        self.is_password = is_password

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Zpracuje pygame událost relevantní pro vstupní pole.

        Klik myší: aktivuje/deaktivuje pole a změní barvu rámečku.
        Klávesa: přidá znak nebo smaže poslední (Backspace).
                 Enter se ignoruje (odesílání řeší tlačítko).

        Args:
            event: Pygame událost z hlavní smyčky.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Aktivuj pole při kliknutí dovnitř, deaktivuj při kliknutí ven
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]    # Smaž poslední znak
            elif event.key != pygame.K_RETURN:
                self.text += event.unicode    # Přidej nový znak (Enter ignorujeme)

    def draw(self, surface: pygame.Surface) -> None:
        """
        Vykreslí vstupní pole na zadaný povrch.

        Obsah pole se zobrazí jako hvězdičky, pokud is_password=True.
        Rámeček mění barvu podle aktivního stavu.

        Args:
            surface: Cílový pygame povrch.
        """
        # Maskuj heslo hvězdičkami
        display_text = "*" * len(self.text) if self.is_password else self.text

        # Vykresli text s odsazením 10 px od levého okraje a 8 px od horního
        txt_surface = self.font.render(display_text, True, (255, 255, 255))
        surface.blit(txt_surface, (self.rect.x + 10, self.rect.y + 8))

        # Vykresli rámeček (tloušťka 2 px)
        pygame.draw.rect(surface, self.color, self.rect, 2)