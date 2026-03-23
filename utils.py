"""
utils.py
========
Pomocné herní funkce používané napříč herní logikou.

Modul obsahuje dvě části:
  1. HelperFunctions — statické metody pro herní logiku (spawn, kolize, částice)
  2. calculate_hit_accuracy — standalone funkce importovaná v render.py

UI komponenty (InputBox, Button) jsou v button.py.
Konstanty pro renderer (RenderState) jsou v render.py.
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

        Args:
            circle1: Střed prvního kruhu.
            circle2: Střed druhého kruhu.
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

        Args:
            pos: Pozice středu výbuchu.
            color: RGB barva částic.
            count: Počet vygenerovaných částic.
            speed: Maximální rychlost částice (px/s).
            lifetime: Životnost každé částice (s).

        Returns:
            list: Seznam slovníků částic.
        """
        new_particles = []
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            vel = pygame.Vector2(
                math.cos(angle), math.sin(angle)
            ) * random.uniform(speed * 0.3, speed)

            new_particles.append({
                'pos':      pos.copy(),
                'vel':      vel,
                'life':     lifetime,
                'max_life': lifetime,
                'color':    color,
                'radius':   random.uniform(2, 5)
            })
        return new_particles

    @staticmethod
    def spawn_damage_text(pos: pygame.Vector2, text,
                          color: tuple = Colors.DAMAGE_TEXT,
                          life: float = 0.7) -> dict:
        """
        Vytvoří plovoucí text zobrazující způsobené poškození.

        Args:
            pos: Počáteční pozice textu.
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
            'vel':      pygame.Vector2(0, -40)
        }

    @staticmethod
    def spawn_enemy_improved() -> 'Enemy':
        """
        Vytvoří nového nepřítele na náhodné straně obrazovky.

        Returns:
            Enemy: Nová instance nepřítele.
        """
        side = random.choice(["left", "right"])
        x = (-GameConfig.ENEMY_RADIUS if side == "left"
             else GameConfig.WIDTH + GameConfig.ENEMY_RADIUS)
        hp = random.randint(GameConfig.ENEMY_MIN_HP, GameConfig.ENEMY_MAX_HP)
        from enemy import Enemy
        return Enemy(x, GameConfig.GROUND_LEVEL, hp=hp)

    @staticmethod
    def spawn_projectile_instance(player_pos: pygame.Vector2,
                                  current_time: int) -> 'Projectile':
        """
        Vytvoří nový projektil namířený od hráče ke kurzoru myši.

        Args:
            player_pos: Aktuální pozice hráče.
            current_time: Aktuální pygame timestamp (ms).

        Returns:
            Projectile: Nová instance projektilu.
        """
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        direction = mouse_pos - player_pos

        if direction.length() > 0:
            direction = direction.normalize()

        direction = direction.rotate_rad(
            random.uniform(-GameConfig.SPREAD, GameConfig.SPREAD)
        )

        color = random.choice(GameConfig.PROJECTILE_COLORS)

        effect_map = {
            Colors.RED:    "explosive",
            Colors.WHITE:  "slow",
            Colors.GREEN:  "dot",
            Colors.PURPLE: "pierce",
            Colors.YELLOW: "heal",
        }
        effect_type = effect_map.get(color, "none")

        from projectiles import Projectile
        return Projectile(
            pos=player_pos.copy(),
            vel=direction * GameConfig.PROJECTILE_SPEED,
            color=color,
            effect_type=effect_type
        )




# =============================================================================
# STANDALONE FUNKCE
# =============================================================================

def calculate_hit_accuracy(hits: int, shots: int) -> float:
    """
    Vypočítá procentuální přesnost zásahů.

    Importována přímo v render.py pro výpočet accuracy v HUD.

    Args:
        hits: Počet úspěšných zásahů.
        shots: Celkový počet výstřelů.

    Returns:
        float: Přesnost v procentech (0.0–100.0+). Při shots=0 vrátí 0.
    """
    if shots == 0:
        return 0
    return (hits / shots) * 100