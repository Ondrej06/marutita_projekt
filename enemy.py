"""
enemy.py
========
Třída Enemy reprezentující nepřátelský objekt.

Nepřátelé se spawnují na okrajích obrazovky a pohybují se přímo
k hráči. Podporují efekty slow (zpomalení pohybu) a dot (damage
over time). Při zásahu vizuálně blikají interpolací barvy.
"""

import math

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
        Vykreslí nepřítele jako stylizovaný energetický kruh s červenou tématikou.

        Pokud je aktivní hurt_timer (nedávný zásah), barva se interpoluje
        od normální červené k bílé — vytváří efekt bliknutí.
        Intenzita bliknutí klesá lineárně s ubývajícím hurt_timerem.

        Args:
            screen: Cílový pygame povrch.
        """
        if not self.is_alive:
            return

        center = (int(self.pos.x), int(self.pos.y))
        r = self.radius

        # Výpočet aktuální barvy podle hurt_timeru (blikání)
        if self.hurt_timer > 0:
            t = max(0.0, min(1.0, self.hurt_timer / self.flash_time))
            # Interpolace: základní červená → bílá
            base_color = Colors.ENEMY  # předpokládám, že Colors.ENEMY je červená
            flash_col = (
                int(base_color[0] + (255 - base_color[0]) * t),
                int(base_color[1] + (255 - base_color[1]) * t),
                int(base_color[2] + (255 - base_color[2]) * t),
            )
        else:
            base_color = Colors.ENEMY
            flash_col = base_color

        # 1. Vnější záře (jemně průhledná)
        glow_radius = r + 4
        glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
        glow_color = (*flash_col[:3], 50)  # použijeme aktuální barvu s alfa 50
        pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
        screen.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius))

        # 2. Hlavní tělo (tmavší varianta aktuální barvy)
        dark_body = (
            max(flash_col[0] - 50, 20),
            max(flash_col[1] - 50, 20),
            max(flash_col[2] - 50, 20)
        )
        pygame.draw.circle(screen, dark_body, center, r)

        # 3. Vnitřní prstenec (světlejší okraj)
        ring_radius = r - 3
        ring_width = 3
        ring_color = (
            min(flash_col[0] + 40, 255),
            min(flash_col[1] + 40, 255),
            min(flash_col[2] + 40, 255)
        )
        pygame.draw.circle(screen, ring_color, center, ring_radius, ring_width)

        # 4. Pulzující jádro (velikost se mění v čase)
        if not hasattr(self, '_last_time'):
            self._last_time = pygame.time.get_ticks()
            self._pulse_phase = 0

        current_time = pygame.time.get_ticks()
        dt = current_time - self._last_time
        self._last_time = current_time
        self._pulse_phase += dt * 0.005  # rychlost pulzování
        core_radius = int(r * (0.5 + 0.2 * (1 + math.sin(self._pulse_phase)) / 2))

        # Středové jádro – sytá, zářivá barva (při blikání bílá)
        core_color = flash_col
        pygame.draw.circle(screen, core_color, center, core_radius)

        # 5. Odlesk (malý bílý bod)
        highlight_radius = max(1, r // 6)
        highlight_offset = r // 3
        highlight_pos = (center[0] - highlight_offset, center[1] - highlight_offset)
        pygame.draw.circle(screen, (255, 255, 255), highlight_pos, highlight_radius)

        # 6. Obrys pro kontrast (použijeme světlejší verzi barvy)
        outline_color = ring_color
        pygame.draw.circle(screen, outline_color, center, r, width=1)

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