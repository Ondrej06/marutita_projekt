import pygame
from config import GameConfig
import math
from visuals import Colors
# ===== TŘÍDA PROJEKTILU =====
class Projectile:
    def __init__(self, pos, vel, color, effect_type="none"):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.radius = GameConfig.PROJECTILE_RADIUS
        self.damage = GameConfig.PROJECTILE_DAMAGE
        self.angle = 0
        self.color = color
        self.trail = []
        self.effect_type = effect_type
        self.hit_targets = []  # Pro průstřelné projektily
        self.is_alive = True
    
    def update(self, dt):
        """Aktualizace pozice a fyziky projektilu"""
        if not self.is_alive:
            return
            
        # Fyzika
        self.vel.y += GameConfig.PROJECTILE_GRAVITY * dt
        self.vel *= (1 - GameConfig.AIR_RESISTANCE * dt)
        self.pos += self.vel * dt
        self.angle = math.degrees(math.atan2(self.vel.y, self.vel.x))
        
        # Stopa
        self.trail.append(self.pos.copy())
        if len(self.trail) > 8:
            self.trail.pop(0)
        
        # Kontrola hranic obrazovky
        if (self.pos.x < -100 or self.pos.x > GameConfig.WIDTH + 100 or
            self.pos.y < -100 or self.pos.y > GameConfig.HEIGHT + 100):
            self.is_alive = False
    
    def draw(self, screen):
        """Vykreslení projektilu a jeho stopy"""
        if not self.is_alive:
            return
            
        # Vykreslení stopy
        for i, pos in enumerate(self.trail):
            alpha = int(200 * (i / len(self.trail)))
            size = 4 if self.color != Colors.GREEN else 6
            glow_color = (*self.color, alpha)
            
            # Vytvoření povrchu s alfa kanálem
            s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, glow_color, (size, size), size)
            screen.blit(s, (pos.x - size, pos.y - size))
        
        # Vykreslení projektilu
        start = self.pos
        end = start + pygame.Vector2(
            math.cos(math.radians(self.angle)),
            math.sin(math.radians(self.angle))
        ) * 12
        pygame.draw.line(screen, self.color, start, end, 3)