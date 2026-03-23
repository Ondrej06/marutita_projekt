"""
states_menu.py
==============
Stavy menu a přihlašovací obrazovky.

Obsahuje všechny stavy, které tvoří "obálku" kolem hry:
  IntroState    — úvodní animace s hyperspace přechodem
  MainMenuState — hlavní menu s tlačítky Play, Settings, Login, Quit
  SettingsState — menu nastavení (grafika, audio)
  GraphicsState — výběr rozlišení obrazovky
  LoginState    — přihlašovací formulář (komunikuje s Flask API)

Rozměry obrazovky se čtou dynamicky přes pygame.display.get_surface().get_size()
v každé metodě — UI prvky tak vždy odpovídají aktuálnímu rozlišení z config.json.

Herní logika je oddělena v states_game.py.
Sdílené základní třídy jsou v states.py.
"""

import math
import pygame
import requests
from threading import Thread

from config import MenuConfig, AppConfig
from visuals import font_cache
from button import Button, InputBox
from states import BaseState, ButtonMenuState, GameState
from settings import load_config, save_config


# =============================================================================
# INTRO STAV
# =============================================================================

class IntroState(BaseState):
    """
    Úvodní animace zobrazující název hry s efektem hyperspace.

    Fáze:
      1. Normální fáze (0–4 s): titulek pulzuje, hint "Press any key".
      2. Hyperspace (po 4 s nebo stisku klávesy): sinusová deformace textu,
         fade to black, přechod do MainMenu.

    Attributes:
        timer (float): Uplynulý čas od vstupu do stavu (s).
        hyperspace (bool): True = aktivní hyperspace animace.
        hyperspace_timer (float): Uplynulý čas hyperspace animace (s).
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0
        self.title = "Bubble Shooter"

    def enter(self, payload=None):
        """Resetuje všechny timery při každém vstupu."""
        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0

    def handle_event(self, event: pygame.event.Event):
        """Klávesa po 2 sekundách přeskočí intro do MainMenu."""
        if event.type == pygame.KEYDOWN and self.timer > 2.0:
            self.manager.change_state(GameState.MAIN_MENU)

    def update(self, dt: float):
        """Aktualizuje timery a spouští hyperspace po 4 sekundách."""
        self.timer += dt

        if self.timer >= 4.0 and not self.hyperspace:
            self.hyperspace = True
            self.hyperspace_timer = 0.0

        if self.hyperspace:
            self.hyperspace_timer += dt
            if self.hyperspace_timer >= MenuConfig.MENU_HYPERSPACE_DURATION:
                self.manager.change_state(GameState.MAIN_MENU)

    def render(self, surface: pygame.Surface):
        """Vykreslí titulek s pulzujícím jasem nebo hyperspace deformací."""
        width, height = pygame.display.get_surface().get_size()
        center_x = width // 2
        center_y = height // 2

        title_font = font_cache.get(96)
        base_surface = title_font.render(self.title, True, (255, 255, 255))
        text_w, text_h = base_surface.get_size()

        if not self.hyperspace:
            pulse = math.sin(self.timer * 1.5) * 20
            alpha = max(0, min(255, int(200 + pulse)))
            base_surface.set_alpha(alpha)
            surface.blit(base_surface, base_surface.get_rect(center=(center_x, center_y)))

            if self.timer > 2.0:
                font = font_cache.get(24)
                hint = font.render("Press any key to skip", True, (120, 120, 120))
                surface.blit(hint, hint.get_rect(center=(center_x, height - 80)))
            return

        # Hyperspace deformace
        warp_power    = min(1.0, self.hyperspace_timer / 1.5)
        warp_strength = int(70 * warp_power)
        slice_h = 2

        for y in range(0, text_h, slice_h):
            current_h = min(slice_h, text_h - y)
            if current_h <= 0:
                continue

            slice_rect = pygame.Rect(0, y, text_w, current_h)
            slice_surf = base_surface.subsurface(slice_rect)

            offset_x = int(math.sin(y * 0.15 + self.hyperspace_timer * 25) * warp_strength)
            scale = 1 + warp_power * 0.8
            warped_slice = pygame.transform.scale(slice_surf, (int(text_w * scale), current_h))

            draw_x = center_x - warped_slice.get_width() // 2 + offset_x
            draw_y = center_y - text_h // 2 + y
            surface.blit(warped_slice, (draw_x, draw_y))

        fade_alpha = min(255, int(self.hyperspace_timer * 180))
        fade = pygame.Surface((width, height))
        fade.fill((0, 0, 0))
        fade.set_alpha(fade_alpha)
        surface.blit(fade, (0, 0))


# =============================================================================
# HLAVNÍ MENU
# =============================================================================

class MainMenuState(ButtonMenuState):
    """
    Hlavní menu s tlačítky Play, Settings, Quit a Login/jméno uživatele.

    Pokud je uživatel přihlášen, tlačítko Login se nahradí jeho
    uživatelským jménem (neaktivní tlačítko jako informační prvek).
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Main Menu"

    def enter(self, payload=None):
        """Sestaví seznam tlačítek; přihlášeného uživatele zobrazí místo Login.
        
        Tlačítka se vytvářejí při každém vstupu, aby jejich pozice
        odpovídaly aktuálnímu rozlišení okna.
        """
        width, height = pygame.display.get_surface().get_size()
        base_buttons = [
            ("Play",     (width // 2, height // 2 - 100), self.on_play),
            ("Settings", (width // 2, height // 2),       self.on_settings),
            ("Quit",     (width // 2, height // 2 + 100), self.on_quit),
            ("Login",    (width // 8, height // 2 - 450), self.on_login),
        ]
        self.buttons = []
        for text, center, action in base_buttons:
            if text == "Login" and self.manager.user_data:
                user_info = self.manager.user_data.get('user', {})
                username  = user_info.get('username', 'User')
                btn = Button(username, center, action=None, base_size=48)
                btn.enabled = False
            else:
                btn = Button(text, center, action, base_size=48)
            self.buttons.append(btn)

    def on_play(self):
        self.manager.change_state(GameState.PLAYING)
        return True

    def on_login(self):
        self.manager.change_state(GameState.LOGIN)
        return True

    def on_settings(self):
        self.manager.change_state(GameState.SETTINGS)
        return True

    def on_quit(self):
        self.manager.running = False
        return True


# =============================================================================
# SETTINGS STAV
# =============================================================================

class SettingsState(ButtonMenuState):
    """Menu nastavení s tlačítky pro grafiku a návrat."""

    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Settings"

    def enter(self, payload=None):
        """Sestaví tlačítka s pozicemi dle aktuálního rozlišení."""
        width, height = pygame.display.get_surface().get_size()
        self.buttons = [
            Button("Graphics", (width // 2, height // 2 - 50), self.on_graphics),
            Button("Back",     (width // 2, height // 2 + 50), self.on_back),
        ]

    def on_graphics(self):
        self.manager.change_state(GameState.GRAPHICS)

    def on_back(self):
        self.manager.change_state(GameState.MAIN_MENU)
        return True


# =============================================================================
# GRAPHICS STAV
# =============================================================================

class GraphicsState(ButtonMenuState):
    """
    Obrazovka pro výběr rozlišení okna.

    Výběr se uloží do config.json a projeví se po restartu aplikace.

    Attributes:
        resolutions (list): Dostupná rozlišení [(šířka, výška), ...].
        current_resolution (tuple): Aktuálně nastavené rozlišení.
        message (str): Informační zpráva po změně rozlišení.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Graphics Settings"
        self.resolutions = [(1920, 1080), (800, 800)]
        self.current_resolution = None
        self.message = ""

    def enter(self, payload=None):
        """Načte aktuální rozlišení z config.json a sestaví tlačítka."""
        config = load_config()
        self.current_resolution = tuple(config["resolution"])
        self.create_buttons()

    def create_buttons(self):
        """Sestaví tlačítka pro každé rozlišení + tlačítko Back."""
        width, height = pygame.display.get_surface().get_size()
        self.buttons = []
        y_start = height // 2 - 100
        for i, (w, h) in enumerate(self.resolutions):
            text = f"{w}x{h}"
            if (w, h) == self.current_resolution:
                text += " (aktivní)"
            btn = Button(
                text,
                (width // 2, y_start + i * 80),
                lambda res=(w, h): self.set_resolution(res)
            )
            self.buttons.append(btn)
        self.buttons.append(Button("Back", (width // 2, height // 2 + 200), self.on_back))

    def set_resolution(self, res: tuple):
        """Uloží nové rozlišení do config.json a obnoví tlačítka."""
        config = load_config()
        config["resolution"] = list(res)
        save_config(config)
        self.message = f"Rozlišení nastaveno na {res[0]}x{res[1]}. Restartujte hru pro uplatnění."
        self.current_resolution = res
        self.create_buttons()

    def on_back(self):
        self.manager.change_state(GameState.SETTINGS)

    def render(self, surface: pygame.Surface):
        """Vykreslí titulek, tlačítka a informační zprávu."""
        super().render(surface)
        if self.message:
            width, height = pygame.display.get_surface().get_size()
            msg_font    = font_cache.get(24)
            msg_surface = msg_font.render(self.message, True, (255, 255, 0))
            surface.blit(msg_surface, msg_surface.get_rect(center=(width // 2, height // 2 + 300)))


# =============================================================================
# LOGIN STAV
# =============================================================================

class LoginState(BaseState):
    """
    Přihlašovací obrazovka komunikující s Flask serverem.

    Přihlašovací požadavek běží v samostatném vlákně (Thread),
    aby neblokoval herní smyčku. Po přihlášení se uloží username
    do config.json pro předvyplnění při příštím spuštění.

    UI prvky (InputBox, Button) se vytváří v enter() — nikoli v __init__() —
    aby jejich pozice vždy odpovídaly aktuálnímu rozlišení okna z config.json.

    Attributes:
        username_box (InputBox): Vstupní pole pro jméno (inicializováno v enter()).
        password_box (InputBox): Vstupní pole pro heslo, maskované (inicializováno v enter()).
        login_button (Button): Odeslání přihlášení (inicializováno v enter()).
        back_button (Button): Návrat do menu (inicializováno v enter()).
        message (str): Stavová zpráva (chyba / úspěch).
        message_color (tuple): RGB barva zprávy.
        is_loading (bool): True = čeká se na server, vstup blokován.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title    = "Login Screen"
        self.base_url = AppConfig.SERVER_URL

        self.message       = ""
        self.message_color = (255, 0, 0)
        self.is_loading    = False

        # UI prvky se inicializují v enter() — rozměry závisí na aktuálním rozlišení
        self.username_box = None
        self.password_box = None
        self.login_button = None
        self.back_button  = None

    def enter(self, payload=None):
        """Vytvoří UI prvky s pozicemi dle aktuálního rozlišení a předvyplní username."""       
        width, height = pygame.display.get_surface().get_size()
        input_font = font_cache.get(32)

        self.username_box = InputBox(
            width // 2 - 200, height // 2 - 40,
            400, 50, input_font
        )
        self.password_box = InputBox(
            width // 2 - 200, height // 2 + 30,
            400, 50, input_font, is_password=True
        )
        self.login_button = Button(
            "Přihlásit", (width // 2, height // 2 + 100),
            action=self.attempt_login, base_size=36
        )
        self.back_button = Button(
            "Zpět", (width // 2, height // 2 + 170),
            action=self.go_back, base_size=30
        )

        config    = load_config()
        last_user = config.get("last_user")
        if last_user:
            self.username_box.text = last_user

    def go_back(self):
        self.manager.change_state(GameState.MAIN_MENU)

    def handle_event(self, event: pygame.event.Event):
        """Zpracuje vstupy — blokuje je během načítání."""
        if self.is_loading:
            return

        self.username_box.handle_event(event)
        self.password_box.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            if self.login_button.rect.collidepoint(pos):
                self.login_button.handle_click()
            elif self.back_button.rect.collidepoint(pos):
                self.back_button.handle_click()

    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        self.login_button.update(dt, mouse_pos)
        self.back_button.update(dt, mouse_pos)

    def render(self, surface: pygame.Surface):
        """Vykreslí přihlašovací formulář."""
        surface.fill((30, 30, 30))

        width, height = pygame.display.get_surface().get_size()

        title_font = font_cache.get(48)
        title_text = title_font.render("Přihlášení", True, (255, 255, 255))
        surface.blit(title_text, title_text.get_rect(center=(width // 2, height // 4)))

        label_font = font_cache.get(24)
        surface.blit(
            label_font.render("Uživatelské jméno:", True, (200, 200, 200)),
            (width // 2 - 200, height // 2 - 70)
        )
        surface.blit(
            label_font.render("Heslo:", True, (200, 200, 200)),
            (width // 2 - 200, height // 2)
        )

        self.username_box.draw(surface)
        self.password_box.draw(surface)
        self.login_button.render(surface)
        self.back_button.render(surface)

        if self.message:
            msg_font = font_cache.get(24)
            msg_text = msg_font.render(self.message, True, self.message_color)
            surface.blit(msg_text, msg_text.get_rect(center=(width // 2, height // 2 + 220)))

        if self.is_loading:
            loading_font = font_cache.get(20)
            loading_text = loading_font.render("Probíhá přihlašování...", True, (255, 255, 0))
            surface.blit(loading_text, loading_text.get_rect(center=(width // 2, height // 2 + 260)))

    def attempt_login(self):
        """Validuje pole a spustí přihlašovací Thread."""
        username = self.username_box.text
        password = self.password_box.text

        if not username or not password:
            self.message       = "Vyplňte všechna pole"
            self.message_color = (255, 0, 0)
            return

        self.is_loading    = True
        self.message       = "Přihlašování..."
        self.message_color = (255, 255, 0)

        Thread(target=self.send_login_request, args=(username, password)).start()

    def send_login_request(self, username: str, password: str):
        """
        Odešle přihlašovací POST na Flask API (běží v samostatném vlákně).

        Args:
            username: Zadané přihlašovací jméno.
            password: Zadané heslo.
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.message       = "Přihlášení úspěšné!"
                self.message_color = (0, 255, 0)

                self.manager.user_data = data

                config = load_config()
                config["last_user"] = data["user"]["username"]
                save_config(config)

                self.manager.change_state(GameState.MAIN_MENU)

            else:
                error_msg          = response.json().get("error", "Neplatné přihlašovací údaje")
                self.message       = error_msg
                self.message_color = (255, 0, 0)

        except requests.exceptions.ConnectionError:
            self.message       = "Nelze se připojit k serveru. Je Flask spuštěný?"
            self.message_color = (255, 0, 0)
        except Exception as e:
            self.message       = f"Chyba: {str(e)}"
            self.message_color = (255, 0, 0)
        finally:
            self.is_loading = False