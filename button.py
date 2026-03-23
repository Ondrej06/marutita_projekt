"""
button.py
=========
UI komponenty pro Pygame menu: Button a InputBox.

Button  — animované textové tlačítko s hover efektem a sinusovým pulzem.
InputBox — textové vstupní pole používané v přihlašovacím formuláři.

Obě třídy jsou vizuální vstupní prvky menu, proto patří do jednoho modulu.
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
        Aktualizuje self.rect pro detekci kolizí v update() a handle_click().

        Args:
            surface: Cílový pygame povrch.

        Returns:
            pygame.Rect: Bounding box vykresleného textu.
        """
        # Sinusový pulz: ±15 bodů jasu synchronizovaný s herním časem
        pulse = math.sin(pygame.time.get_ticks() / 1000.0 * 2 * math.pi) * 15

        display_color = int(max(0, min(255, self.color_value + pulse)))

        font = font_cache.get(self.font_size)
        text_surface = font.render(self.text, True, (display_color,) * 3)

        self.rect = text_surface.get_rect(center=self.center)
        surface.blit(text_surface, self.rect)

        return self.rect


# =============================================================================
# VSTUPNÍ POLE
# =============================================================================

class InputBox:
    """
    Interaktivní textové vstupní pole pro Pygame UI.

    Používá se v LoginState pro zadání uživatelského jména a hesla.
    Podporuje zobrazení hesla jako hvězdiček (is_password=True).

    Attributes:
        rect (pygame.Rect): Ohraničující obdélník pole.
        color (pygame.Color): Aktuální barva rámečku (šedá = neaktivní, bílá = aktivní).
        text (str): Aktuální obsah pole.
        active (bool): True = pole přijímá klávesové vstupy.
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
        self.color_inactive = pygame.Color('gray')
        self.color_active   = pygame.Color('white')
        self.color = self.color_inactive
        self.text = ""
        self.font = font
        self.active = False
        self.is_password = is_password

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Zpracuje pygame událost relevantní pro vstupní pole.

        Klik myší: aktivuje/deaktivuje pole.
        Klávesa: přidá znak nebo smaže poslední (Backspace). Enter je ignorován.

        Args:
            event: Pygame událost z hlavní smyčky.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key != pygame.K_RETURN:
                self.text += event.unicode

    def draw(self, surface: pygame.Surface) -> None:
        """
        Vykreslí vstupní pole na zadaný povrch.

        Args:
            surface: Cílový pygame povrch.
        """
        display_text = "*" * len(self.text) if self.is_password else self.text

        txt_surface = self.font.render(display_text, True, (255, 255, 255))
        surface.blit(txt_surface, (self.rect.x + 10, self.rect.y + 8))
        pygame.draw.rect(surface, self.color, self.rect, 2)


# =============================================================================
# ZVUKOVÉ EFEKTY (rezerva pro budoucí implementaci)
# =============================================================================

def play_hover_sound() -> None:
    """Přehraje zvukový efekt při najetí myší na tlačítko. (Zatím nevyužito.)"""
    pass


def play_click_sound() -> None:
    """Přehraje zvukový efekt při kliknutí na tlačítko. (Zatím nevyužito.)"""
    pass