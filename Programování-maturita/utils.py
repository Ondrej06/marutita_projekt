import pygame
import math
import random
from config import GameConfig
from visuals import Colors

class HelperFunctions:
    """Třída obsahující pomocné funkce pro hru."""
    
    @staticmethod
    def check_collision(circle1, circle2, r1, r2):
        """Detekce kolize dvou kruhů."""
        return circle1.distance_to(circle2) < (r1 + r2)
    
    @staticmethod
    def spawn_hit_particles(pos, color, count=12, speed=200, lifetime=0.5):
        """Vytvoření efektu částic."""
        new_particles = []
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(speed * 0.3, speed)
            new_particles.append({
                'pos': pos.copy(),
                'vel': vel,
                'life': lifetime,
                'max_life': lifetime,
                'color': color,
                'radius': random.uniform(2, 5)
            })
        return new_particles
    
    @staticmethod
    def spawn_damage_text(pos, text, color=Colors.DAMAGE_TEXT, life=0.7):
        """Vytvoření plovoucího textu poškození."""
        return {
            'pos': pos.copy(),
            'text': str(text),
            'life': life,
            'max_life': life,
            'vel': pygame.Vector2(0, -40)
        }
    
    @staticmethod
    def spawn_enemy_improved():
        """Vytvoření nepřítele na náhodné straně obrazovky."""
        side = random.choice(["left", "right"])
        x = -GameConfig.ENEMY_RADIUS if side == "left" else GameConfig.WIDTH + GameConfig.ENEMY_RADIUS
        hp = random.randint(GameConfig.ENEMY_MIN_HP, GameConfig.ENEMY_MAX_HP)
        from enemy import Enemy  # Lokální import, aby se předešlo cyklické závislosti
        return Enemy(x, GameConfig.GROUND_LEVEL, hp=hp)
    
    @staticmethod
    def spawn_projectile_instance(player_pos, current_time):
        """Vytvoření nového projektilu."""
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        direction = mouse_pos - player_pos
        
        if direction.length() > 0:
            direction = direction.normalize()
        
        # Přidání náhodného rozptylu
        direction = direction.rotate_rad(random.uniform(-GameConfig.SPREAD, GameConfig.SPREAD))
        
        # Náhodná barva a efekt
        color = random.choice(GameConfig.PROJECTILE_COLORS)
        effect_map = {
            Colors.RED: "explosive",
            Colors.WHITE: "slow", 
            Colors.GREEN: "dot",
            Colors.PURPLE: "pierce",
            Colors.YELLOW: "heal"
        }
        effect_type = effect_map.get(color, "none")
        
        # Vytvoření projektilu
        from projectiles import Projectile  # Lokální import
        projectile = Projectile(
            pos=player_pos.copy(),
            vel=direction * GameConfig.PROJECTILE_SPEED,
            color=color,
            effect_type=effect_type
        )
        
        return projectile
    
    @staticmethod
    def calculate_accuracy(stats_dict):
        """Vypočítá přesnost zásahů."""
        if stats_dict.get("projectiles_fired", 0) > 0:
            return (stats_dict.get("projectiles_hit", 0) / stats_dict.get("projectiles_fired", 1)) * 100
        return 0.0
    
    @staticmethod
    def is_off_screen(pos, margin=50):
        """Zkontroluje, zda je pozice mimo obrazovku."""
        return (pos.x < -margin or pos.x > GameConfig.WIDTH + margin or 
                pos.y < -margin or pos.y > GameConfig.HEIGHT + margin)
    
    @staticmethod
    def lerp_color(color1, color2, t):
        """Lineární interpolace mezi dvěma barvami."""
        r = int(color1[0] + (color2[0] - color1[0]) * t)
        g = int(color1[1] + (color2[1] - color1[1]) * t)
        b = int(color1[2] + (color2[2] - color1[2]) * t)
        return (r, g, b)
    
    @staticmethod
    def format_time(seconds):
        """Formátuje čas ve vteřinách do čitelného formátu MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
"""
Pomocné funkce pro hru
"""

def calculate_hit_accuracy(hits, shots):
    """
    Vypočítá procentuální přesnost zásahů
    """
    if shots == 0:
        return 0
    return (hits / shots) * 100


class GameState:
    """
    Stav hry - třída s konstantami
    """
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    # Přidej další stavy podle potřeby