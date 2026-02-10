import pygame
from config import GameConfig
from visuals import Colors
# ===== TŘÍDA HRÁČE =====
class Player:
    def __init__(self):
        self.pos = pygame.Vector2(GameConfig.WIDTH // 2, GameConfig.GROUND_LEVEL)
        self.velocity = pygame.Vector2(0, 0)
        self.health = GameConfig.PLAYER_MAX_HEALTH
        self.max_health = GameConfig.PLAYER_MAX_HEALTH
        self.radius = GameConfig.PLAYER_RADIUS
        
        # Stavy
        self.iframe = 0  # Doba nezranitelnosti
        self.knockback = pygame.Vector2(0, 0)
        self.dashing = False
        self.dash_direction = 0
        self.dash_time = 0
        self.last_dash_time = 0
        self.dash_trail = []
        
        # Výdrž
        self.stamina = GameConfig.MAX_STAMINA
    
    def update(self, dt):
        """Aktualizace stavu hráče"""
        # Aplikace odhození
        self.pos += self.knockback * dt
        self.knockback *= (1 - 6 * dt)
        
        # Snížení času nezranitelnosti
        if self.iframe > 0:
            self.iframe -= dt
        
        # Aktualizace dash efektů
        self.update_dash_trail(dt)
    
    def move(self, dt, keys):
        """Zpracování pohybu hráče"""
        if not self.dashing:
            # Normální pohyb do stran
            if keys[pygame.K_d]:
                self.pos.x += GameConfig.PLAYER_SPEED * dt
            if keys[pygame.K_a]:
                self.pos.x -= GameConfig.PLAYER_SPEED * dt
        
        # Dash logika
        if keys[pygame.K_LCTRL] and not self.dashing:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_dash_time >= GameConfig.DASH_COOLDOWN:
                if keys[pygame.K_d]:
                    self.dash_direction = 1
                elif keys[pygame.K_a]:
                    self.dash_direction = -1
                else:
                    self.dash_direction = 0
                
                if self.dash_direction != 0:
                    self.dashing = True
                    self.dash_time = 0
                    self.last_dash_time = current_time
        
        # Běh dash
        if self.dashing:
            self.pos.x += self.dash_direction * GameConfig.DASH_SPEED * dt
            self.dash_time += dt
            if self.dash_time >= GameConfig.DASH_DURATION:
                self.dashing = False
    
    def fly(self, dt, keys):
        """Zpracování létání"""
        if keys[pygame.K_SPACE] and self.stamina > 0:
            self.velocity.y = -GameConfig.FLY_LIFT
            self.stamina -= GameConfig.STAMINA_USE * dt
        else:
            self.velocity.y += GameConfig.GRAVITY * dt
            if self.pos.y >= GameConfig.GROUND_LEVEL:
                self.stamina = min(GameConfig.MAX_STAMINA, 
                                 self.stamina + GameConfig.STAMINA_REGEN * dt)
        
        self.pos.y += self.velocity.y * dt
    
    def update_dash_trail(self, dt):
        """Aktualizace efektu stopy za dashem"""
        # Odstranění starých bodů
        for point in self.dash_trail[:]:
            point[1] -= dt
            if point[1] <= 0:
                self.dash_trail.remove(point)
        
        # Přidání nových bodů během dashe
        if self.dashing:
            for i in range(GameConfig.DASH_TRAIL_LENGTH):
                offset = -i * 6
                trail_pos = self.pos + pygame.Vector2(offset * self.dash_direction, 0)
                alpha = 255 * (1 - i / GameConfig.DASH_TRAIL_LENGTH)
                self.dash_trail.append([trail_pos, GameConfig.DASH_TRAIL_LIFETIME, alpha])
    
    def draw(self, screen):
        """Vykreslení hráče"""
        pygame.draw.circle(screen, Colors.PLAYER_DEFAULT, 
                          (int(self.pos.x), int(self.pos.y)), self.radius)
    
    def draw_dash_trail(self, screen):
        """Vykreslení stopy za dashem"""
        for point in self.dash_trail:
            pos, life, alpha = point
            current_alpha = int(alpha * (life / GameConfig.DASH_TRAIL_LIFETIME))
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*Colors.WHITE, current_alpha), 
                             (self.radius, self.radius), self.radius)
            screen.blit(s, (pos.x - self.radius, pos.y - self.radius))
    
    def take_damage(self, damage, direction):
        """Zpracování přijetí poškození"""
        if self.iframe <= 0:
            self.health -= damage
            self.iframe = 0.4
            self.knockback = direction.normalize() * 400
    
    def heal(self, amount):
        """Léčení hráče"""
        self.health = min(self.health + amount, self.max_health)
    
    def enforce_boundaries(self):
        """Udržení hráče v herních hranicích"""
        self.pos.x = max(self.radius, 
                        min(GameConfig.WIDTH - self.radius, self.pos.x))
        self.pos.y = min(GameConfig.GROUND_LEVEL, self.pos.y)