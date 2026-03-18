"""
enemy.py
========
Třída Enemy reprezentující nepřátelský objekt.

Nepřátelé se spawnují na okrajích obrazovky a pohybují se přímo
k hráči. Podporují efekty slow (zpomalení pohybu) a dot (damage
over time). Při zásahu vizuálně blikají interpolací barvy.
"""

import pygame
from visuals import Colors
from config import GameConfig


class Enemy:
    """
    Nepřátelský objekt pronásledující hráče.

    Pohybuje se konstantní rychlostí ve směru k hráči. Může být
    zasažen efekty slow nebo dot, které ovlivňují jeho rychlost
    respektive zdraví v průběhu času.

    Attributes:
        pos (pygame.Vector2): Aktuální pozice středu nepřítele (px).
        radius (int): Poloměr kolizní kružnice.
        health (float): Aktuální zdraví.
        max_health (float): Maximální zdraví (pro případné vykreslení health baru).
        hurt_timer (float): Zbývající čas blikání po zásahu (s).
        flash_time (float): Celková délka blikacího efektu (s).
        slow_timer (float): Zbývající čas zpomalení (s).
        slow_factor (float): Aktuální multiplikátor rychlosti (1.0 = normální, 0.5 = pomalý).
        dot_timer (float): Zbývající čas DoT efektu (s).
        dot_damage (float): Poškození DoT za sekundu.
        is_alive (bool): False = nepřítel je mrtvý a čeká na odstranění ze seznamu.
    """

    def __init__(self, x: float, y: float, hp: int = 60):
        """
        Inicializuje nepřítele na zadané pozici.

        Args:
            x: Počáteční X souřadnice (px).
            y: Počáteční Y souřadnice — obvykle GROUND_LEVEL.
            hp: Počáteční zdraví. Výchozí hodnota 60, max 100 (viz GameConfig).
        """
        self.pos = pygame.Vector2(x, y)
        self.radius = GameConfig.ENEMY_RADIUS
        self.health = hp
        self.max_health = hp

        # ── Vizuální efekty ────────────────────────────────────────────────
        self.hurt_timer = 0.0           # Odpočítává zbývající čas bliknutí po zásahu
        self.flash_time = GameConfig.HURT_FLASH_TIME  # Celková délka bliknutí

        # ── Efekt zpomalení (slow) ─────────────────────────────────────────
        self.slow_timer = 0             # Zbývající čas zpomalení (s)
        self.slow_factor = 1            # 1.0 = plná rychlost, 0.5 = polovina

        # ── Efekt DoT (damage over time) ──────────────────────────────────
        self.dot_timer = 0              # Zbývající čas DoT efektu (s)
        self.dot_damage = 0             # HP odečtená za každou sekundu DoT

        # Rezerva pro budoucí AoE efekty
        self.aoe_effects = []

        # Příznak life — herní smyčka na základě toho odstraní nepřítele
        self.is_alive = True

    # =========================================================================
    # AKTUALIZACE
    # =========================================================================

    def update(self, dt: float, player_pos: pygame.Vector2) -> None:
        """
        Aktualizuje pozici a všechny aktivní efekty nepřítele.

        Pořadí operací:
          1. Pohyb směrem k hráči (s aplikací slow faktoru).
          2. Odečtení DoT poškození.
          3. Odpočítání slow timeru (reset faktoru po vypršení).
          4. Odpočítání hurt timeru (vizuální blikání).
          5. Kontrola smrti (health <= 0).

        Args:
            dt: Delta time v sekundách.
            player_pos: Aktuální pozice hráče pro výpočet směru pohybu.
        """
        if not self.is_alive:
            return  # Mrtvý nepřítel se nepohybuje ani neaktualizuje

        # ── Pohyb k hráči ─────────────────────────────────────────────────
        direction = player_pos - self.pos
        if direction.length() > 0:
            # Normalizuj směrový vektor a přičti ke pohybu
            # slow_factor: 1.0 = plná rychlost, <1.0 = zpomaleno
            speed = GameConfig.ENEMY_SPEED * self.slow_factor
            self.pos += direction.normalize() * speed * dt

        # ── Damage over Time ──────────────────────────────────────────────
        if self.dot_timer > 0:
            self.health -= self.dot_damage * dt  # Poškození úměrné uplynulému času
            self.dot_timer -= dt

        # ── Zpomalení ─────────────────────────────────────────────────────
        if self.slow_timer > 0:
            self.slow_timer -= dt
        else:
            self.slow_factor = 1  # Obnovení plné rychlosti po vypršení slow efektu

        # ── Hurt timer (blikání) ──────────────────────────────────────────
        if self.hurt_timer > 0:
            self.hurt_timer -= dt

        # ── Kontrola smrti ────────────────────────────────────────────────
        if self.health <= 0:
            self.is_alive = False  # Herní smyčka nepřítele odstraní a vytvoří částice

    # =========================================================================
    # VYKRESLOVÁNÍ
    # =========================================================================

    def draw(self, screen: pygame.Surface) -> None:
        """
        Vykreslí nepřítele jako kruh.

        Pokud je aktivní hurt_timer (nedávný zásah), barva se interpoluje
        od normální ENEMY barvy k bílé — vytváří efekt bliknutí.
        Intenzita bliknutí klesá lineárně s ubývajícím hurt_timerem.

        Args:
            screen: Cílový pygame povrch.
        """
        if not self.is_alive:
            return

        if self.hurt_timer > 0:
            # t: 1.0 = zrovna zasažen (plně bílý), 0.0 = efekt skončil
            t = max(0.0, min(1.0, self.hurt_timer / self.flash_time))

            # Lineární interpolace barvy: ENEMY → bílá podle t
            flash_col = (
                int(Colors.ENEMY[0] + (255 - Colors.ENEMY[0]) * t),
                int(Colors.ENEMY[1] + (255 - Colors.ENEMY[1]) * t),
                int(Colors.ENEMY[2] + (255 - Colors.ENEMY[2]) * t),
            )
            pygame.draw.circle(screen, flash_col, (int(self.pos.x), int(self.pos.y)), self.radius)
        else:
            # Normální barva bez efektu
            pygame.draw.circle(screen, Colors.ENEMY, (int(self.pos.x), int(self.pos.y)), self.radius)

    # =========================================================================
    # EFEKTY — VOLÁNY Z HERNÍ SMYČKY
    # =========================================================================

    def take_damage(self, damage: float) -> None:
        """
        Odečte zdraví a spustí vizuální hurt efekt (bliknutí).

        Args:
            damage: Množství HP k odečtení.
        """
        self.health -= damage
        self.hurt_timer = self.flash_time  # Restartuje blikací efekt

    def apply_slow(self, duration: float, factor: float) -> None:
        """
        Aplikuje efekt zpomalení pohybu.

        Nepřítel se pohybuje rychlostí ENEMY_SPEED * factor po dobu duration sekund.
        Volá se při zásahu bílým (slow) projektilem.

        Args:
            duration: Délka trvání zpomalení v sekundách.
            factor: Multiplikátor rychlosti (0.5 = 50 % normální rychlosti).
        """
        self.slow_timer = duration
        self.slow_factor = factor

    def apply_dot(self, duration: float, damage_per_second: float) -> None:
        """
        Aplikuje efekt Damage over Time.

        Nepřítel ztrácí damage_per_second HP každou sekundu po dobu duration sekund.
        Volá se při zásahu zeleným (dot) projektilem.

        Args:
            duration: Délka trvání DoT efektu v sekundách.
            damage_per_second: HP odečtená za každou sekundu.
        """
        self.dot_timer = duration
        self.dot_damage = damage_per_second