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
    INTRO = auto(); MAIN_MENU = auto(); PLAYING = auto(); SETTINGS = auto()

class BaseState:
    def __init__(self, manager): self.manager = manager
    def enter(self,payload=None): pass
    def exit(self): pass
    def handle_event(self,event): pass
    def update(self,dt): pass
    def render(self,surface): pass

class IntroState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title="Název Hry"
        self.instr="Stiskni jakoukoliv klávesu"
        self.hyperspace=False; self.hyperspace_timer=0.0
    def handle_event(self,event):
        if event.type==pygame.KEYDOWN and not self.hyperspace:
            self.hyperspace=True; self.hyperspace_timer=0.0
    def update(self,dt):
        if self.hyperspace:
            self.hyperspace_timer+=dt
            if self.hyperspace_timer>=MenuConfig.MENU_HYPERSPACE_DURATION:
                self.manager.change_state(GameState.MAIN_MENU)
    def render(self,surface):
        title_font=font_cache.get(96)
        title_surface=title_font.render(self.title,True,(255,255,255))
        surface.blit(title_surface,title_surface.get_rect(center=(width//2,height//4)))
        pulse=int(math.sin(pygame.time.get_ticks()/1000.0*math.pi)*50)
        instr_font=font_cache.get(48)
        instr_surface=instr_font.render(self.instr,True,(max(0,min(255,255+pulse)),)*3)
        surface.blit(instr_surface,instr_surface.get_rect(center=(width//2,height//2)))

class MainMenuState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.buttons=[Button("Play",(width//2,height//2-100),self.on_play),
                      Button("Settings",(width//2,height//2),self.on_settings),
                      Button("Quit",(width//2,height//2+100),self.on_quit)]
    def on_play(self): self.manager.change_state(GameState.PLAYING); return True
    def on_settings(self): self.manager.change_state(GameState.SETTINGS); return True
    def on_quit(self): self.manager.running=False; return True
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos): b.handle_click()
    def update(self,dt):
        pos=pygame.mouse.get_pos()
        for b in self.buttons: b.update(dt,pos)
    def render(self,surface):
        for b in self.buttons: b.render(surface)

class PlayingState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title="GAME IS RUNNING"
        self.back_btn=Button("Back to Menu",(width//2,height//2+200),self.on_back,42)
    def on_back(self): self.manager.change_state(GameState.MAIN_MENU); return True
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=pygame.mouse.get_pos()
            if self.back_btn.rect.collidepoint(pos): self.back_btn.handle_click()
    def update(self,dt):
        pos=pygame.mouse.get_pos()
        self.back_btn.update(dt,pos)
    def render(self,surface):
        title_font=font_cache.get(72)
        title_surface=title_font.render(self.title,True,(255,255,255))
        surface.blit(title_surface,title_surface.get_rect(center=(width//2,height//2)))
        self.back_btn.render(surface)

class SettingsState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title="Settings"
        self.buttons=[Button("Graphics",(width//2,height//2-100),self.on_graphics),
                      Button("Audio",(width//2,height//2),self.on_audio),
                      Button("Back",(width//2,height//2+100),self.on_back)]
    def on_graphics(self): print("Graphics pressed"); return True
    def on_audio(self): print("Audio pressed"); return True
    def on_back(self): self.manager.change_state(GameState.MAIN_MENU); return True
    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos): b.handle_click()
    def update(self,dt):
        pos=pygame.mouse.get_pos()
        for b in self.buttons: b.update(dt,pos)
    def render(self,surface):
        title_font=font_cache.get(72)
        title_surface=title_font.render(self.title,True,(255,255,255))
        surface.blit(title_surface,title_surface.get_rect(center=(width//2,height//4)))
        for b in self.buttons: b.render(surface)