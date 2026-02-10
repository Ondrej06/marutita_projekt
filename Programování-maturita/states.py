import math
import pygame
from enum import Enum, auto
from config import MenuConfig
from visuals import font_cache
from button import Button

width, height = MenuConfig.MENU_SCREEN_WIDTH, MenuConfig.MENU_SCREEN_HEIGHT

# -------------------------
# GAME STATES
# -------------------------
class GameState(Enum):
    INTRO = auto()
    MAIN_MENU = auto()
    PLAYING = auto()
    SETTINGS = auto()

# -------------------------
# BASE STATE
# -------------------------
class BaseState:
    def __init__(self, manager): 
        self.manager = manager
    def enter(self,payload=None): pass
    def exit(self): pass
    def handle_event(self,event): pass
    def update(self,dt): pass
    def render(self,surface): pass

# -------------------------
# INTRO STATE (CINEMATIC / WARP)
# -------------------------
class IntroState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)

        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0
        self.title = "udfzstgfjzsdrgfjsdffgsdifgfuidgfudfdfgfdjhdfhj"

    def enter(self, payload=None):
        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.timer > 2.0:
            self.manager.change_state(GameState.MAIN_MENU)

    def update(self, dt):
        self.timer += dt

        # hyperspace start
        if self.timer >= 4.0 and not self.hyperspace:
            self.hyperspace = True
            self.hyperspace_timer = 0.0

        if self.hyperspace:
            self.hyperspace_timer += dt
            if self.hyperspace_timer >= MenuConfig.MENU_HYPERSPACE_DURATION:
                self.manager.change_state(GameState.MAIN_MENU)

    def render(self, surface):
        center_x = width // 2
        center_y = height // 2

        title_font = font_cache.get(96)
        base_surface = title_font.render(self.title, True, (255, 255, 255))
        text_w, text_h = base_surface.get_size()

        # ---------------------
        # NORMAL STATE (pulsing)
        # ---------------------
        if not self.hyperspace:
            pulse = math.sin(self.timer * 1.5) * 20
            alpha = max(0, min(255, int(200 + pulse)))
            base_surface.set_alpha(alpha)
            surface.blit(
                base_surface,
                base_surface.get_rect(center=(center_x, center_y)),
            )

            if self.timer > 2.0:
                font = font_cache.get(24)
                hint = font.render("Press any key to skip", True, (120, 120, 120))
                surface.blit(hint, hint.get_rect(center=(center_x, height - 80)))
            return

        # ---------------------
        # HYPERSPACE WARP EFFECT
        # ---------------------
        warp_power = min(1.0, self.hyperspace_timer / 1.5)
        warp_strength = int(70 * warp_power)
        slice_h = 2  # výška pásů

        for y in range(0, text_h, slice_h):
            current_h = min(slice_h, text_h - y)
            if current_h <= 0: 
                continue

            slice_rect = pygame.Rect(0, y, text_w, current_h)
            slice_surf = base_surface.subsurface(slice_rect)

            # sinusová deformace
            offset_x = int(math.sin(y * 0.15 + self.hyperspace_timer * 25) * warp_strength)
            scale = 1 + warp_power * 0.8
            warped_slice = pygame.transform.scale(slice_surf, (int(text_w * scale), current_h))

            draw_x = center_x - warped_slice.get_width() // 2 + offset_x
            draw_y = center_y - text_h // 2 + y
            surface.blit(warped_slice, (draw_x, draw_y))

        # fade
        fade_alpha = min(255, int(self.hyperspace_timer * 180))
        fade = pygame.Surface((width, height))
        fade.fill((0, 0, 0))
        fade.set_alpha(fade_alpha)
        surface.blit(fade, (0, 0))

# -------------------------
# MAIN MENU STATE
# -------------------------
class MainMenuState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Main Menu"
        self.buttons = [
            Button("Play", (width//2, height//2-100), self.on_play),
            Button("Settings", (width//2, height//2), self.on_settings),
            Button("Quit", (width//2, height//2+100), self.on_quit)
        ]

    def on_play(self): 
        self.manager.change_state(GameState.PLAYING)
        return True
    def on_settings(self): 
        self.manager.change_state(GameState.SETTINGS)
        return True
    def on_quit(self): 
        self.manager.running = False
        return True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos): b.handle_click()

    def update(self, dt):
        pos = pygame.mouse.get_pos()
        for b in self.buttons: b.update(dt, pos)

    def render(self, surface):
        title_font = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width//2, height//4)))
        for b in self.buttons: b.render(surface)

# -------------------------
# PLAYING STATE
# -------------------------
class PlayingState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title = "GAME IS RUNNING"
        self.back_btn = Button("Back to Menu", (width//2, height//2+200), self.on_back, 42)

    def on_back(self): 
        self.manager.change_state(GameState.MAIN_MENU)
        return True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            if self.back_btn.rect.collidepoint(pos):
                self.back_btn.handle_click()

    def update(self, dt):
        pos = pygame.mouse.get_pos()
        self.back_btn.update(dt, pos)

    def render(self, surface):
        title_font = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width//2, height//2)))
        self.back_btn.render(surface)

# -------------------------
# SETTINGS STATE
# -------------------------
class SettingsState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Settings"
        self.buttons = [
            Button("Graphics", (width//2, height//2-100), self.on_graphics),
            Button("Audio", (width//2, height//2), self.on_audio),
            Button("Back", (width//2, height//2+100), self.on_back)
        ]

    def on_graphics(self): 
        print("Graphics pressed")
        return True
    def on_audio(self): 
        print("Audio pressed")
        return True
    def on_back(self): 
        self.manager.change_state(GameState.MAIN_MENU)
        return True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos): b.handle_click()

    def update(self, dt):
        pos = pygame.mouse.get_pos()
        for b in self.buttons: b.update(dt, pos)

    def render(self, surface):
        title_font = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width//2, height//4)))
        for b in self.buttons: b.render(surface)
