"""
button.py
=========
Třída Button pro interaktivní tlačítka v Pygame menu.

Tlačítka reagují na pohyb myši plynulou animací (zvětšení textu,
zvýšení jasu) a sinusovým pulzem pro živý look. Každé tlačítko
má přiřazenou akci (callable), která se zavolá při kliknutí.
"""

import math
import pygame
from visuals import font_cache


class Button:
    """
    Animované textové tlačítko pro Pygame UI.

    Animace jsou řešeny exponenciální interpolací (lerp) — hodnoty
    se plynule přibližují cílovému stavu každý snímek.
    Dodatečný sinusový pulz zabraňuje statickému vzhledu.

    Attributes:
        text (str): Zobrazený text tlačítka.
        center (tuple): Střed tlačítka (x, y) v px.
        action (callable | None): Funkce zavolaná při kliknutí.
        base_size (int): Základní velikost písma v bodech.
        font_size (float): Aktuální (interpolovaná) velikost písma.
        target_size (int): Cílová velikost písma (base nebo 125 % při hoveru).
        color_value (float): Aktuální (interpolovaná) hodnota jasu (0–255).
        target_color (int): Cílový jas (200 = normální, 255 = hover).
        was_hovered (bool): Stav z minulého snímku — detekce vstupu kurzoru.
        rect (pygame.Rect): Bounding box textu — aktualizuje se při vykreslení.
        enabled (bool): False = tlačítko je neaktivní (nezajímá hover ani kliknutí).
    """

    def __init__(self, text: str, center: tuple, action=None, base_size: int = 48):
        """
        Args:
            text: Text zobrazený na tlačítku.
            center: Souřadnice středu tlačítka (x, y).
            action: Funkce/lambda zavolaná při kliknutí. None = žádná akce.
            base_size: Základní velikost písma v bodech.
        """
        self.text = text
        self.center = center
        self.action = action
        self.base_size = base_size

        # Počáteční stav animace — shodný se základními hodnotami
        self.font_size = float(base_size)
        self.target_size = base_size
        self.color_value = 200.0     # Výchozí jas (šedavě bílá)
        self.target_color = 200.0

        self.was_hovered = False
        self.rect = pygame.Rect(0, 0, 0, 0)  # Inicializuje se při prvním render()
        self.enabled = True

    def update(self, dt: float, mouse_pos: tuple) -> bool:
        """
        Aktualizuje animační stav tlačítka na základě pozice myši.

        Logika:
          - Detekuje hover (kolize kurzoru s rect).
          - Při novém vstupu kurzoru přehraje hover zvuk.
          - Plynule interpoluje velikost písma a jas k cílovým hodnotám.

        Args:
            dt: Delta time v sekundách.
            mouse_pos: Aktuální pozice kurzoru (x, y).

        Returns:
            bool: True pokud je kurzor nad tlačítkem.
        """
        if not self.enabled:
            return False

        hovered = self.rect.collidepoint(mouse_pos)

        # Zvukový efekt pouze při prvním vstupu kurzoru (náběžná hrana)
        if hovered and not self.was_hovered:
            play_hover_sound()

        # Nastav cílové hodnoty animace podle stavu hoveru
        self.target_size  = int(self.base_size * 1.25) if hovered else self.base_size
        self.target_color = 255 if hovered else 200

        # Exponenciální interpolace k cílovým hodnotám (lerp faktor 10/s)
        # Vzorec: current += (target - current) * factor * dt
        # Při dt=1/144 a faktoru 10: každý snímek se přiblíží o ~6,7 %
        self.font_size = (
            min(max(self.font_size, 0), self.target_size)
            + (self.target_size - self.font_size) * dt * 10
        )
        self.color_value = (
            min(max(self.color_value, 0), self.target_color)
            + (self.target_color - self.color_value) * dt * 10
        )

        self.was_hovered = hovered
        return hovered

    def handle_click(self):
        """
        Zavolá přiřazenou akci tlačítka a přehraje klikací zvuk.

        Volá se z handle_event() stavu, když hráč klikne na tlačítko.
        Pokud tlačítko nemá akci nebo není enabled, nic se nestane.

        Returns:
            Návratová hodnota akce, nebo False pokud akce neexistuje.
        """
        if self.enabled and self.action:
            play_click_sound()
            return self.action()
        return False

    def render(self, surface: pygame.Surface) -> pygame.Rect:
        """
        Vykreslí tlačítko na zadaný povrch.

        Barva textu pulzuje sinusovou funkcí pro živý, dynamický vzhled.
        Velikost fontu je interpolovaná hodnota z update() — plynulá animace.
        Aktualizuje self.rect pro detekci kolizí v update() a handle_click().

        Args:
            surface: Cílový pygame povrch.

        Returns:
            pygame.Rect: Bounding box vykresleného textu (pro debug/kliknutí).
        """
        # Sinusový pulz: ±15 bodů jasu synchronizovaný s herním časem
        pulse = math.sin(pygame.time.get_ticks() / 1000.0 * 2 * math.pi) * 15

        # Výsledná barva: interpolovaná hodnota + pulz, oříznutá na 0–255
        display_color = int(max(0, min(255, self.color_value + pulse)))

        # Získej font ze cache pro aktuální (animovanou) velikost
        font = font_cache.get(self.font_size)
        text_surface = font.render(self.text, True, (display_color,) * 3)

        # Umísti text na střed tlačítka a aktualizuj rect
        self.rect = text_surface.get_rect(center=self.center)
        surface.blit(text_surface, self.rect)

        return self.rect


# =============================================================================
# ZVUKOVÉ EFEKTY (zatím prázdné — rezerva pro budoucí implementaci)
# =============================================================================

def play_hover_sound() -> None:
    """Přehraje zvukový efekt při najetí myší na tlačítko. (Zatím nevyužito.)"""
    pass


def play_click_sound() -> None:
    """Přehraje zvukový efekt při kliknutí na tlačítko. (Zatím nevyužito.)"""
    pass