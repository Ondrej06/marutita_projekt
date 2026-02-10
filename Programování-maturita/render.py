import pygame
import math
from config import GameConfig
from visuals import Colors
from utils import calculate_hit_accuracy  # Import z utils
from utils import GameState  # Pokud máš GameState v utils.py

# ===== TŘÍDA PRO VYKRESLOVÁNÍ =====
class Renderer:
    def __init__(self, screen):
        pygame.font.init()  # PŘIDEJ TENTO ŘÁDEK
        self.screen = screen
        self.font = pygame.font.SysFont(None, 24)
        self.large_font = pygame.font.SysFont(None, 72)
        self.medium_font = pygame.font.SysFont(None, 36)
        
        # UI interpolace
        self.smooth_hp = 0
        self.smooth_st = 0
    
    def draw_particles(self, particles):
        """Vykreslení částic"""
        for p in particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            s = pygame.Surface((p['radius']*2, p['radius']*2), pygame.SRCALPHA)
            pygame.draw.circle(s, p['color'] + (alpha,), 
                             (int(p['radius']), int(p['radius'])), int(p['radius']))
            self.screen.blit(s, (p['pos'].x - p['radius'], p['pos'].y - p['radius']))
    
    def draw_damage_texts(self, damage_texts):
        """Vykreslení plovoucích textů poškození"""
        for t in damage_texts:
            alpha = int(255 * (t['life'] / t['max_life']))
            txt_surf = self.font.render(str(t['text']), True, Colors.DAMAGE_TEXT)
            txt_surf.set_alpha(alpha)
            self.screen.blit(txt_surf, (t['pos'].x, t['pos'].y))
    
    def draw_projectiles(self, projectiles):
        """Vykreslení všech projektilů"""
        for projectile in projectiles:
            projectile.draw(self.screen)
    
    def draw_health_bar(self, player, dt):
        """Vykreslení health baru"""
        # Interpolace pro plynulost
        self.smooth_hp += (player.health - self.smooth_hp) * 10 * dt
        hp_percent = max(0, self.smooth_hp / player.max_health)
        
        # Pozadí baru
        pygame.draw.rect(self.screen, Colors.UI_BG, (20, 50, 220, 22), border_radius=5)
        
        # Barva podle stavu zdraví
        if hp_percent > 0.6:
            color = Colors.GREEN
        elif hp_percent > 0.3:
            color = (255, 210, 0)
        else:
            color = Colors.RED
        
        # Výplň baru
        pygame.draw.rect(self.screen, color, (20, 50, 220 * hp_percent, 22), border_radius=5)
        
        # Text
        hp_text = self.font.render(f"{int(self.smooth_hp)} / {player.max_health}", True, Colors.WHITE)
        self.screen.blit(hp_text, (25, 52))
    
    def draw_stamina_bar(self, player, dt):
        """Vykreslení stamina baru"""
        self.smooth_st += (player.stamina - self.smooth_st) * 10 * dt
        st_percent = self.smooth_st / GameConfig.MAX_STAMINA
        
        # Pozadí
        pygame.draw.rect(self.screen, Colors.UI_BG, (20, 80, 220, 18), border_radius=5)
        
        # Výplň
        pygame.draw.rect(self.screen, Colors.STAMINA, (20, 80, 220 * st_percent, 18), border_radius=5)
        
        # Text
        st_text = self.font.render(f"Stamina: {int(player.stamina)}", True, Colors.WHITE)
        self.screen.blit(st_text, (25, 82))
    
    def draw_dash_cooldown(self, player, current_time):
        """Vykreslení indikátoru cooldownu dashe"""
        dash_cooldown_progress = min(1.0, 
            (current_time - player.last_dash_time) / GameConfig.DASH_COOLDOWN)
        center_x, center_y = 50, 120
        radius = 15
        
        if dash_cooldown_progress < 1.0:
            pygame.draw.circle(self.screen, Colors.UI_BG, (center_x, center_y), radius)
            end_angle = -math.pi/2 + 2 * math.pi * dash_cooldown_progress
            pygame.draw.arc(self.screen, Colors.WHITE, 
                          (center_x-radius, center_y-radius, radius*2, radius*2), 
                          -math.pi/2, end_angle, 3)
            cd_text = self.font.render(
                f"{int((1 - dash_cooldown_progress) * (GameConfig.DASH_COOLDOWN / 1000))}s", 
                True, Colors.WHITE)
            self.screen.blit(cd_text, (center_x - 8, center_y - 6))
        else:
            pygame.draw.circle(self.screen, Colors.GREEN, (center_x, center_y), radius)
            ready_text = self.font.render("D", True, Colors.WHITE)
            self.screen.blit(ready_text, (center_x - 5, center_y - 6))
    
    def draw_game_stats(self, stats):
        """Vykreslení statistik"""
        # SPRÁVNÉ VOLÁNÍ FUNKCE - předáváme 2 parametry
        hits = stats.get("projectiles_hit", 0)
        shots = stats.get("projectiles_fired", 0)
        accuracy = calculate_hit_accuracy(hits, shots)
        
        stats_text = [
            f"Kills: {stats.get('enemies_killed', 0)}",
            f"Accuracy: {accuracy:.1f}%",  # Formátujeme na 1 desetinné místo
            f"Projectiles: {shots}",
            f"Hits: {hits}",
            f"Collisions: {stats.get('player_collisions', 0)}"
        ]
        
        for i, text in enumerate(stats_text):
            stat_surf = self.font.render(text, True, Colors.WHITE)
            self.screen.blit(stat_surf, (GameConfig.WIDTH - 200, 50 + i * 25))
    
    def draw_fps_counter(self, current_fps, show_fps, fps_history):
        """Vykreslení FPS čítače"""
        if not show_fps:
            return
        
        fps_history.append(current_fps)
        if len(fps_history) > 100:
            fps_history.pop(0)
        
        # Barva podle FPS
        if current_fps >= 60:
            color = Colors.GREEN
        elif current_fps >= 30:
            color = Colors.YELLOW
        else:
            color = Colors.RED
        
        fps_text = self.font.render(f"FPS: {int(current_fps)}", True, color)
        self.screen.blit(fps_text, (20, 20))
    
    def draw_game_overlay(self, current_state):
        """Vykreslení overlay pro pauzu a game over"""
        if current_state == GameState.PAUSED:
            overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            self.screen.blit(overlay, (0, 0))
            
            paused_text = self.large_font.render("PAUSED", True, Colors.WHITE)
            text_rect = paused_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2))
            self.screen.blit(paused_text, text_rect)
        
        elif current_state == GameState.GAME_OVER:
            overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 192))
            self.screen.blit(overlay, (0, 0))
            
            msg = self.large_font.render("GAME OVER", True, Colors.RED)
            msg_rect = msg.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 - 50))
            self.screen.blit(msg, msg_rect)
            
            restart_text = self.medium_font.render("Press R to restart", True, Colors.GREEN)
            restart_rect = restart_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 + 150))
            self.screen.blit(restart_text, restart_rect)