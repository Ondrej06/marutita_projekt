import math
import pygame
from visuals import font_cache
# -------------------------
# BUTTON
# -------------------------
class Button:
    def __init__(self, text, center, action=None, base_size=48):
        self.text = text
        self.center = center
        self.action = action
        self.base_size = base_size
        self.font_size = base_size
        self.target_size = base_size
        self.color_value = 200.0
        self.target_color = 200.0
        self.was_hovered = False
        self.rect = pygame.Rect(0,0,0,0)
        self.enabled = True
    def update(self, dt, mouse_pos):
        if not self.enabled: return False
        hovered = self.rect.collidepoint(mouse_pos)
        if hovered and not self.was_hovered: play_hover_sound()
        self.target_size = int(self.base_size*1.25) if hovered else self.base_size
        self.target_color = 255 if hovered else 200
        self.font_size = min(max(self.font_size,0), self.target_size) + (self.target_size-self.font_size)*dt*10
        self.color_value = min(max(self.color_value,0), self.target_color) + (self.target_color-self.color_value)*dt*10
        self.was_hovered = hovered
        return hovered
    def handle_click(self):
        if self.enabled and self.action:
            play_click_sound()
            return self.action()
        return False
    def render(self, surface):
        pulse = math.sin(pygame.time.get_ticks()/1000.0*2*math.pi)*15
        display_color = int(max(0,min(255,self.color_value + pulse)))
        font = font_cache.get(self.font_size)
        text_surface = font.render(self.text, True, (display_color,)*3)
        self.rect = text_surface.get_rect(center=self.center)
        surface.blit(text_surface, self.rect)
        return self.rect

def play_hover_sound(): pass
def play_click_sound(): pass