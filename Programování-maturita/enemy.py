import pygame
from visuals import Colors
from config import GameConfig

# ===== TŘÍDA NEPŘÍTELE =====
class Enemy:
    def __init__(self, x, y, hp=60):
        self.pos = pygame.Vector2(x, y)
        self.radius = GameConfig.ENEMY_RADIUS
        self.health = hp
        self.max_health = hp
        
        # Stavy a efekty
        self.hurt_timer = 0.0
        self.flash_time = GameConfig.HURT_FLASH_TIME
        self.slow_timer = 0
        self.slow_factor = 1
        self.dot_timer = 0
        self.dot_damage = 0
        self.aoe_effects = []
        self.is_alive = True
    
    def update(self, dt, player_pos):
        """Aktualizace pozice a stavů nepřítele"""
        if not self.is_alive:
            return
            
        # Pohyb směrem k hráči se zpomalením
        direction = player_pos - self.pos
        if direction.length() > 0:
            speed = GameConfig.ENEMY_SPEED * self.slow_factor
            self.pos += direction.normalize() * speed * dt
        
        # Aplikace Damage over Time
        if self.dot_timer > 0:
            self.health -= self.dot_damage * dt
            self.dot_timer -= dt
        
        # Správa zpomalení
        if self.slow_timer > 0:
            self.slow_timer -= dt
        else:
            self.slow_factor = 1
        
        # Aktualizace časovače zranění
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
        
        # Kontrola smrti
        if self.health <= 0:
            self.is_alive = False
    
    def draw(self, screen):
        """Vykreslení nepřítele"""
        if not self.is_alive:
            return
            
        if self.hurt_timer > 0:
            # Bliknutí při zásahu
            t = max(0.0, min(1.0, self.hurt_timer / self.flash_time))
            flash_col = (
                int(Colors.ENEMY[0] + (255 - Colors.ENEMY[0]) * t),
                int(Colors.ENEMY[1] + (255 - Colors.ENEMY[1]) * t),
                int(Colors.ENEMY[2] + (255 - Colors.ENEMY[2]) * t)
            )
            pygame.draw.circle(screen, flash_col, (int(self.pos.x), int(self.pos.y)), self.radius)
        else:
            pygame.draw.circle(screen, Colors.ENEMY, (int(self.pos.x), int(self.pos.y)), self.radius)
    
    def take_damage(self, damage):
        """Zpracování přijetí poškození"""
        self.health -= damage
        self.hurt_timer = self.flash_time
    
    def apply_slow(self, duration, factor):
        """Aplikace zpomalení"""
        self.slow_timer = duration
        self.slow_factor = factor
    
    def apply_dot(self, duration, damage_per_second):
        """Aplikace Damage over Time"""
        self.dot_timer = duration
        self.dot_damage = damage_per_second