"""
projectiles.py
==============
Třída Projectile pro střely vystřelené hráčem.

Každý projektil má fyzikální simulaci (gravitace + vzdušný odpor),
vizuální stopu a typ efektu určující speciální chování při zásahu.
Barva projektilu odpovídá jeho efektu (mapování viz utils.py).
"""

import pygame
import math
from config import GameConfig
from visuals import Colors


class Projectile:
    """
    Střela vystřelená hráčem směrem ke kurzoru myši.

    Fyzika:
      - Gravitace zvětšuje vertikální rychlost každý snímek (padabola).
      - Vzdušný odpor exponenciálně tlumí celkovou rychlost.
      - Výsledkem je balistická křivka — je nutné mířit s nadhledem.

    Vizuál:
      - Stopa (trail) ukládá posledních 8 pozic a vykresluje je jako
        průhledné kruhy s narůstající alpha (starší = průhledné).
      - Samotný projektil je čárka ve směru pohybu (realistická střela).

    Attributes:
        pos (pygame.Vector2): Aktuální pozice.
        vel (pygame.Vector2): Aktuální rychlostní vektor (px/s).
        radius (int): Poloměr pro detekci kolizí.
        damage (int): Základní poškození při zásahu.
        angle (float): Aktuální úhel pohybu ve stupních (pro vykreslení čárky).
        color (tuple): RGB barva — určuje vizuál i typ efektu.
        trail (list): Posledních 8 pozic pro stopu.
        effect_type (str): Typ speciálního efektu: 'none','explosive','slow','dot','pierce','heal'.
        hit_targets (list): Seznam Enemy zasažených tímto projektilem.
                            Pro 'pierce' typ — zabrání dvojitému zásahu téhož nepřítele.
        is_alive (bool): False = projektil opustil obrazovku nebo zasáhl cíl.
    """

    def __init__(self, pos: pygame.Vector2, vel: pygame.Vector2,
                 color: tuple, effect_type: str = "none"):
        """
        Inicializuje projektil na dané pozici s danou rychlostí.

        Args:
            pos: Počáteční pozice (obvykle pozice hráče).
            vel: Počáteční rychlostní vektor — směr a rychlost střely.
            color: RGB barva — vizuál i identifikátor efektu.
            effect_type: Typ efektu ('none', 'explosive', 'slow', 'dot', 'pierce', 'heal').
        """
        self.pos = pygame.Vector2(pos)   # Kopie, ne reference
        self.vel = pygame.Vector2(vel)
        self.radius = GameConfig.PROJECTILE_RADIUS
        self.damage = GameConfig.PROJECTILE_DAMAGE
        self.angle = 0                   # Aktualizuje se v update() pro směrovou čárku
        self.color = color
        self.trail = []                  # Fronta posledních poloh pro vizuální stopu
        self.effect_type = effect_type
        self.hit_targets = []            # Zasažení nepřátelé (pro pierce typ)
        self.is_alive = True

    # =========================================================================
    # AKTUALIZACE FYZIKY
    # =========================================================================

    def update(self, dt: float) -> None:
        """
        Simuluje pohyb projektilu jedním krokem fyzikální integrace.

        Postup výpočtu (Eulerova metoda):
          1. Zvětši vertikální složku rychlosti o gravitaci.
          2. Zmenši celkovou rychlost o vzdušný odpor.
          3. Posuň projektil dle aktuální rychlosti.
          4. Vypočítej úhel pro vykreslení (atan2).
          5. Přidej aktuální pozici do stopy (max 8 bodů).
          6. Zkontroluj, zda projektil opustil obrazovku.

        Args:
            dt: Delta time v sekundách.
        """
        if not self.is_alive:
            return

        # ── Fyzika ────────────────────────────────────────────────────────
        # Gravitace: zvyšuje vertikální rychlost (kladná Y = dolů)
        self.vel.y += GameConfig.PROJECTILE_GRAVITY * dt

        # Vzdušný odpor: každý snímek zmenší rychlost o malé procento
        # Faktor (1 - c*dt) je aproximace e^(-c*t) — exponenciální útlum
        self.vel *= (1 - GameConfig.AIR_RESISTANCE * dt)

        # Eulerova integrace: posun = rychlost × čas
        self.pos += self.vel * dt

        # Úhel pohybu — pro vykreslení čárky ve směru letu
        self.angle = math.degrees(math.atan2(self.vel.y, self.vel.x))

        # ── Stopa (trail) ─────────────────────────────────────────────────
        self.trail.append(self.pos.copy())
        if len(self.trail) > 8:
            self.trail.pop(0)  # Udržuj maximálně 8 historických pozic (FIFO)

        # ── Kontrola hranic ───────────────────────────────────────────────
        # Margin 100 px zabrání předčasnému zániku projektilu na okraji obrazovky
        if (self.pos.x < -100 or self.pos.x > GameConfig.WIDTH + 100 or
                self.pos.y < -100 or self.pos.y > GameConfig.HEIGHT + 100):
            self.is_alive = False

    # =========================================================================
    # VYKRESLOVÁNÍ
    # =========================================================================

    def draw(self, screen: pygame.Surface) -> None:
        """
        Vykreslí vizuální stopu a samotný projektil.

        Stopa:
          - Každý historický bod se vykreslí jako průhledný kruh.
          - Alpha (průhlednost) roste s indexem — starší body jsou průhledné,
            novější (blíže k projektilu) jsou více viditelné.
          - Zelené projektily (dot efekt) mají větší stopu (size=6 vs size=4).

        Projektil:
          - Vykreslí se jako krátká čárka (12 px) ve směru pohybu.
          - Čárka působí jako realistická střela v pohybu.

        Args:
            screen: Cílový pygame povrch.
        """
        if not self.is_alive:
            return

        # ── Stopa ─────────────────────────────────────────────────────────
        for i, pos in enumerate(self.trail):
            # Alpha narůstá s pozicí v seznamu (0 = nejstarší = průhledný)
            alpha = int(200 * (i / len(self.trail)))

            # Zelené projektily mají větší stopu pro zdůraznění DoT efektu
            size = 6 if self.color == Colors.GREEN else 4

            # Povrch s alfa kanálem pro průhledný kruh
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (size, size), size)
            screen.blit(s, (pos.x - size, pos.y - size))

        # ── Projektil (čárka ve směru pohybu) ─────────────────────────────
        start = self.pos
        # Koncový bod: posun 12 px ve směru pohybu
        end = start + pygame.Vector2(
            math.cos(math.radians(self.angle)),
            math.sin(math.radians(self.angle))
        ) * 12
        pygame.draw.line(screen, self.color, start, end, 3)