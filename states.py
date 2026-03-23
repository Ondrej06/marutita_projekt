"""
states.py
=========
Základní stavební bloky State Machine.

Tento modul obsahuje pouze sdílené třídy, ze kterých dědí všechny stavy:
  - GameState  — enum všech možných obrazovek aplikace
  - BaseState  — abstraktní základ s prázdnými metodami
  - ButtonMenuState — základ pro stavy s menu tlačítky

Rozměry obrazovky se čtou dynamicky přes pygame.display.get_surface().get_size()
v každé render() metodě — respektuje rozlišení nastavené v config.json.

Konkrétní stavy jsou v:
  states_menu.py — IntroState, MainMenuState, SettingsState, GraphicsState, LoginState
  states_game.py — PlayingState
"""

import pygame
from enum import Enum, auto

from visuals import font_cache
from button import Button


# =============================================================================
# VÝČET HERNÍCH STAVŮ
# =============================================================================

class GameState(Enum):
    """
    Výčet všech možných stavů aplikace.

    Hodnoty jsou automaticky generovaná celá čísla (auto()).
    Používají se jako klíče v StateManager.states slovníku.
    """
    INTRO     = auto()   # Úvodní animace s názvem hry
    MAIN_MENU = auto()   # Hlavní menu (Play, Settings, Login, Quit)
    PLAYING   = auto()   # Aktivní hra
    SETTINGS  = auto()   # Menu nastavení
    LOGIN     = auto()   # Přihlašovací obrazovka
    GRAPHICS  = auto()   # Výběr rozlišení obrazovky


# =============================================================================
# ZÁKLADNÍ TŘÍDA STAVU
# =============================================================================

class BaseState:
    """
    Abstraktní základ pro všechny herní stavy.

    Implementuje prázdné verze všech metod — potomci přepíší
    jen ty metody, které potřebují.

    Attributes:
        manager: Reference na StateManager pro přechody mezi stavy.
    """

    def __init__(self, manager):
        self.manager = manager

    def enter(self, payload=None): pass
    def exit(self):                pass
    def handle_event(self, event): pass
    def update(self, dt):          pass
    def render(self, surface):     pass


# =============================================================================
# ZÁKLADNÍ STAV S TLAČÍTKY
# =============================================================================

class ButtonMenuState(BaseState):
    """
    Mezilehlá základní třída pro stavy s menu tlačítky.

    MainMenuState, SettingsState a GraphicsState sdílí identické
    chování pro zpracování kliknutí, aktualizaci animací a základní
    vykreslení titulku + tlačítek. Místo kopírování těchto metod
    do každého stavu je definují zde jednou.

    Potomci mohou přepsat render() pro přidání vlastních prvků —
    stačí zavolat super().render(surface) a pak dokreslit vlastní obsah.

    Attributes:
        title (str): Text nadpisu zobrazený v horní části obrazovky.
        buttons (list): Seznam Button instancí stavu.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title   = ""
        self.buttons = []

    def handle_event(self, event: pygame.event.Event):
        """Zpracuje klik levým tlačítkem myši na tlačítko."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos):
                    b.handle_click()

    def update(self, dt: float):
        """Aktualizuje animační stav všech tlačítek."""
        pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, pos)

    def render(self, surface: pygame.Surface):
        """Vykreslí titulek stavu a všechna tlačítka.
        
        Rozměry se čtou dynamicky — respektuje rozlišení z config.json.
        """
        # Rozměry se čtou dynamicky — respektuje rozlišení z config.json
        width, height = pygame.display.get_surface().get_size()
        title_font    = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width // 2, height // 4)))
        for b in self.buttons:
            b.render(surface)