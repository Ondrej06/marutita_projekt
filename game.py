import pygame
import math
import random
import json
from config import GameConfig
from visuals import Colors
from path import Path

pygame.init()
# ===== GAME STATE =====
class GameState:
    PLAYING = 0
    GAME_OVER = 1
    PAUSED = 2

# Initialize screen
screen = pygame.display.set_mode((GameConfig.WIDTH, GameConfig.HEIGHT))
pygame.display.set_caption("Projectile Combat Game")
clock = pygame.time.Clock()
running = True
current_state = GameState.PLAYING

# FPS tracking
fps_history = []
max_fps_history = 100  # Uchovávání posledních 100 FPS hodnot
current_fps = 0
show_fps = True  # Přepínač pro zobrazení FPS

# Načtení obrázku
try:
    background_image = pygame.image.load(Path.background).convert_alpha()
    background_image = pygame.transform.scale(background_image, (GameConfig.WIDTH, GameConfig.HEIGHT))
except:
    # Fallback pokud obrázek neexistuje
    background_image = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT))
    background_image.fill((50, 50, 80))

# Smooth UI!!!!
smooth_hp = GameConfig.PLAYER_MAX_HEALTH
smooth_st = GameConfig.STAMINA_BAR

# Player combat!!
player_iframe = 0
player_knockback = pygame.Vector2(0,0)

# Létání!!
stamina = GameConfig.MAX_STAMINA
stamina_use = GameConfig.STAMINA_USE
stamina_regen = GameConfig.STAMINA_REGEN

# Dash
dashing = False
dash_direction = 0
dash_speed = GameConfig.DASH_SPEED
dash_duration = GameConfig.DASH_DURATION
dash_time = 0
dash_cooldown = GameConfig.DASH_COOLDOWN
last_dash_time = 0
dash_trail = []
dash_trail_lifetime = GameConfig.DASH_TRAIL_LIFETIME
dash_trail_length = GameConfig.DASH_TRAIL_LENGTH

# Projektily
projectile_speed = GameConfig.PROJECTILE_SPEED
projectile_radius = GameConfig.PROJECTILE_RADIUS
projectile_damage = GameConfig.PROJECTILE_DAMAGE
projectiles = []
projectile_delay = GameConfig.PROJECTILE_DELAY
last_projectile_time = 0
hit_heal = GameConfig.HIT_HEAL

# Nepřátelé
enemies = []
last_enemy_spawn_time = pygame.time.get_ticks()

# Efekty
hit_effects = []
particles = []
damage_texts = []

# Statistiky
stats = {
    "enemies_killed": 0,
    "player_collisions": 0,
    "projectiles_fired": 0,
    "projectiles_hit": 0,
}

# Fonty
font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 72)
medium_font = pygame.font.SysFont(None, 36)

def calculate_hit_accuracy():
    if stats["projectiles_fired"] == 0:
        return 0
    return round(stats["projectiles_hit"] / stats["projectiles_fired"] * 100, 2)

# Kolize
def check_collision(circle1, circle2, r1, r2):
    return circle1.distance_to(circle2) < (r1 + r2)

def spawn_hit_particles(pos, color, count=12, speed=200, lifetime=0.5):
    for _ in range(count):
        angle = random.uniform(0, math.pi*2)
        vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(speed*0.3, speed)
        particles.append({'pos': pos.copy(),'vel': vel,'life': lifetime,'max_life': lifetime,'color': color,'radius': random.uniform(2,5)})

def spawn_damage_text(pos, text, color=Colors.DAMAGE_TEXT, life=0.7):
    damage_texts.append({'pos': pos.copy(),'text': str(text),'life': life,'max_life': life,'vel': pygame.Vector2(0, -40)})

def spawn_enemy(x, y, hp=60):
    return {'pos': pygame.Vector2(x, y),
            'radius': GameConfig.ENEMY_RADIUS,
            'health': hp,
            'max_health': hp,
            'hurt_timer':0.0,
            'flash_time':GameConfig.HURT_FLASH_TIME,
            'slow_timer':0,
            'slow_factor':1,
            'dot_timer':0,
            'dot_damage':0,
            'aoe_effects': []}

def spawn_enemy_improved():
    side = random.choice(["left", "right"])
    if side == "left":
        x = -GameConfig.ENEMY_RADIUS
    else:
        x = GameConfig.WIDTH + GameConfig.ENEMY_RADIUS
    
    hp = random.randint(GameConfig.ENEMY_MIN_HP, GameConfig.ENEMY_MAX_HP)
    return spawn_enemy(x, GameConfig.GROUND_LEVEL, hp=hp)

def enforce_boundaries():
    GameConfig.PLAYER_POSITION_Y.x = max(GameConfig.PLAYER_RADIUS, 
                      min(GameConfig.WIDTH - GameConfig.PLAYER_RADIUS, GameConfig.PLAYER_POSITION_Y.x))
    GameConfig.PLAYER_POSITION_Y.y = min(GameConfig.GROUND_LEVEL, GameConfig.PLAYER_POSITION_Y.y)

def update_dash_trail():
    global dash_trail
    
    for point in dash_trail[:]:
        point[1] -= dt
        if point[1] <= 0:
            dash_trail.remove(point)
    
    # Add new trail points during dash
    if dashing:
        for i in range(GameConfig.DASH_TRAIL_LENGTH):
            offset = -i * 6
            trail_pos = GameConfig.PLAYER_POSITION_Y + pygame.Vector2(offset * dash_direction, 0)
            # Use gradient based on position in trail
            alpha = 255 * (1 - i / GameConfig.DASH_TRAIL_LENGTH)
            dash_trail.append([trail_pos, GameConfig.DASH_TRAIL_LIFETIME, alpha])

def handle_projectile_collision(projectile, enemy):
    if projectile.get('effect_type') == "pierce":
        if enemy in projectile['hit_targets']:
            return False  # Already hit this enemy
        projectile['hit_targets'].append(enemy)
    else:
        if projectile in projectiles:
            projectiles.remove(projectile)
    
    return True  # Collision handled

# ===== GAME STATE MANAGEMENT =====
def handle_game_events():
    global running, current_state, show_fps
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if current_state == GameState.PLAYING:
                    current_state = GameState.PAUSED
                elif current_state == GameState.PAUSED:
                    current_state = GameState.PLAYING
            elif event.key == pygame.K_r and current_state == GameState.GAME_OVER:
                reset_game()
            elif event.key == pygame.K_F1:  # Přidáno: Přepínání FPS display
                show_fps = not show_fps
        
        if current_state == GameState.PLAYING:
            handle_playing_events(event)

def handle_playing_events(event):
    global last_projectile_time
    
    if event.type == pygame.MOUSEBUTTONDOWN:
        if current_time - last_projectile_time >= GameConfig.PROJECTILE_DELAY:
            spawn_projectile()

def spawn_projectile():
    global last_projectile_time
    
    mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
    direction = mouse_pos - GameConfig.PLAYER_POSITION_Y
    if direction.length() > 0:
        direction = direction.normalize()
    direction = direction.rotate_rad(random.uniform(-GameConfig.SPREAD, GameConfig.SPREAD))
    
    color = random.choice(GameConfig.PROJECTILE_COLORS)
    
    # Map colors to effects
    effect_map = {
        Colors.RED: "explosive",
        Colors.WHITE: "slow", 
        Colors.GREEN: "dot",
        Colors.PURPLE: "pierce",
        Colors.YELLOW: "heal"
    }
    effect_type = effect_map.get(color, "none")
    
    projectile = {
        'pos': GameConfig.PLAYER_POSITION_Y.copy(),
        'vel': direction * GameConfig.PROJECTILE_SPEED,
        'radius': GameConfig.PROJECTILE_RADIUS,
        'damage': GameConfig.PROJECTILE_DAMAGE,
        'angle': 0,
        'color': color,
        'trail': [],
        'effect_type': effect_type,
        'hit_targets': []
    }
    projectiles.append(projectile)
    last_projectile_time = current_time
    stats["projectiles_fired"] += 1

def update_game_state():
    global current_state
    GameConfig.PLAYER_MAX_HEALTH
    
    if GameConfig.PLAYER_MAX_HEALTH <= 0 and current_state != GameState.GAME_OVER:
        current_state = GameState.GAME_OVER
    
    if current_state == GameState.PLAYING:
        update_playing_state()

def reset_game():

    global  enemies, projectiles, particles, damage_texts
    global current_state, stats, dash_trail, dashing, player_iframe, player_knockback, dash_direction, dash_time
    
    
    enemies.clear()
    projectiles.clear()
    particles.clear()
    damage_texts.clear()
    dash_trail.clear()
    dashing = False
    dash_direction = 0
    dash_time = 0
    player_iframe = 0
    player_knockback = pygame.Vector2(0,0)
    current_state = GameState.PLAYING
    
    # Reset stats
    stats = {
        "enemies_killed": 0,
        "player_collisions": 0,
        "projectiles_fired": 0,
        "projectiles_hit": 0,
    }

def update_playing_state():

    global  stamina, dashing, dash_time, last_dash_time
    global  player_iframe, player_knockback, last_enemy_spawn_time
    global dash_direction
    
    # Movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_d] and not dashing:
        GameConfig.PLAYER_POSITION_Y.x += GameConfig.PLAYER_SPEED * dt
    if keys[pygame.K_a] and not dashing:
        GameConfig.PLAYER_POSITION_Y.x -= GameConfig.PLAYER_SPEED * dt

    if keys[pygame.K_LCTRL] and not dashing:
        if current_time - last_dash_time >= GameConfig.DASH_COOLDOWN:
            if keys[pygame.K_d]:
                dash_direction = 1
            elif keys[pygame.K_a]:
                dash_direction = -1
            else:
                dash_direction = 0
            if dash_direction != 0:
                dashing = True
                dash_time = 0
                last_dash_time = current_time

    if dashing:
        GameConfig.PLAYER_POSITION_Y.x += dash_direction * dash_speed * dt
        dash_time += dt
        if dash_time >= dash_duration:
            dashing = False

    # Fly
    if keys[pygame.K_SPACE] and stamina > 0:
        GameConfig.PLAYER_VELOCITY_Y = -GameConfig.FLY_LIFT
        stamina -= GameConfig.STAMINA_USE * dt
        if stamina < 0:
            stamina = 0
    else:
        GameConfig.PLAYER_VELOCITY_Y += GameConfig.GRAVITY * dt
        if GameConfig.PLAYER_POSITION_Y.y >= GameConfig.GROUND_LEVEL:
            stamina += GameConfig.STAMINA_REGEN * dt
            if stamina > GameConfig.MAX_STAMINA:
                stamina = GameConfig.MAX_STAMINA

    GameConfig.PLAYER_POSITION_Y.y += GameConfig.PLAYER_VELOCITY_Y * dt
    if GameConfig.PLAYER_POSITION_Y.y > GameConfig.GROUND_LEVEL:
        GameConfig.PLAYER_POSITION_Y.y = GameConfig.GROUND_LEVEL
        GameConfig.PLAYER_VELOCITY_Y = 0
    # Spawn enemies
    if current_time - last_enemy_spawn_time >= GameConfig.ENEMY_SPAWN_INTERVAL:
        enemies.append(spawn_enemy_improved())
        last_enemy_spawn_time = current_time

    # Player-enemy collision
    for enemy in enemies:
        direction = GameConfig.PLAYER_POSITION_Y - enemy['pos']
        if direction.length() < GameConfig.PLAYER_RADIUS + enemy['radius']:
            if player_iframe <= 0:
                GameConfig.PLAYER_MAX_HEALTH -= 15
                player_iframe = 0.4
                player_knockback = direction.normalize() * 400
                stats["player_collisions"] += 1

    if player_iframe > 0:
        player_iframe -= dt
        Colors.PLAYER_DEFAULT = Colors.PLAYER_HURT
    else:
        Colors.PLAYER_DEFAULT = Colors.PLAYER_DEFAULT

    GameConfig.PLAYER_POSITION_Y += player_knockback * dt
    player_knockback *= (1 - 6 * dt)

    # Enemy movement & DoT
    for enemy in enemies:
        direction = GameConfig.PLAYER_POSITION_Y - enemy['pos']
        if direction.length() > 0:
            enemy['pos'] += direction.normalize() * GameConfig.ENEMY_SPEED * dt * enemy.get('slow_factor',1)
        if enemy.get('dot_timer',0) > 0:
            enemy['health'] -= enemy.get('dot_damage',0) * dt
            enemy['dot_timer'] -= dt
        if enemy.get('slow_timer',0) > 0:
            enemy['slow_timer'] -= dt
        else:
            enemy['slow_factor'] = 1

    # Projectiles
    for projectile in projectiles[:]:
        projectile['vel'].y += GameConfig.PROJECTILE_GRAVITY * dt
        projectile['vel'] *= (1 - GameConfig.AIR_RESISTANCE * dt)
        projectile['pos'] += projectile['vel'] * dt
        projectile['angle'] = math.degrees(math.atan2(projectile['vel'].y,projectile['vel'].x))
        projectile['trail'].append(projectile['pos'].copy())
        if len(projectile['trail'])>8:
            projectile['trail'].pop(0)

        for enemy in enemies[:]:
            if check_collision(projectile['pos'], enemy['pos'], projectile['radius'], enemy['radius']):
                if not handle_projectile_collision(projectile, enemy):
                    continue

                dmg = projectile.get('damage', projectile_damage)
                enemy['health'] -= dmg
                enemy['hurt_timer'] = enemy['flash_time']
                stats["projectiles_hit"] += 1
                spawn_hit_particles(enemy['pos'], Colors.HIT_PARTICLES, count=10, speed=220, lifetime=0.4)
                spawn_damage_text(enemy['pos']-pygame.Vector2(0,enemy['radius']+10), dmg)

                if projectile.get('effect_type') == "explosive":
                    for e in enemies:
                        if e['pos'].distance_to(enemy['pos']) <= 50:
                            e['health'] -= dmg//2
                            spawn_hit_particles(e['pos'], Colors.EXPLOSIVE_PARTICLES, count=6)
                elif projectile.get('effect_type') == "slow":
                    enemy['slow_timer'] = GameConfig.SLOW_DURATION
                    enemy['slow_factor'] = GameConfig.SLOW_FACTOR
                elif projectile.get('effect_type') == "dot":
                    enemy['dot_timer'] = GameConfig.DOT_DURATION
                    enemy['dot_damage'] = dmg * GameConfig.DOT_DAMAGE_FACTOR
                elif projectile.get('effect_type') == "heal":
                    GameConfig.PLAYER_MAX_HEALTH += hit_heal
                    if GameConfig.PLAYER_MAX_HEALTH > GameConfig.PLAYER_MAX_HEALTH:
                        GameConfig.PLAYER_MAX_HEALTH = GameConfig.PLAYER_MAX_HEALTH

                if enemy['health'] <= 0:
                    spawn_hit_particles(enemy['pos'], Colors.DEATH_PARTICLES, count=20, speed=400, lifetime=0.7)
                    try: enemies.remove(enemy)
                    except ValueError: pass
                    stats["enemies_killed"] += 1

    # Effects update
    for p in particles[:]:
        p['life'] -= dt
        if p['life']<=0:
            particles.remove(p)
            continue
        p['pos'] += p['vel'] * dt
        p['vel'] *= (1 - 3 * dt)

    for t in damage_texts[:]:
        t['life'] -= dt
        if t['life']<=0:
            damage_texts.remove(t)
            continue
        t['pos'] += t['vel'] * dt
        t['vel'] *= (1 - 1.5 * dt)

    # Update dash trail
    update_dash_trail()
    
    # Enforce boundaries
    enforce_boundaries()

# ===== DRAWING FUNCTIONS =====
def draw_dash_trail():
    for point in dash_trail:
        pos, life, alpha = point
        current_alpha = int(alpha * (life / GameConfig.DASH_TRAIL_LIFETIME))
        # Single color with gradient
        color = (*Colors.WHITE, current_alpha)
        s = pygame.Surface((GameConfig.PLAYER_RADIUS * 2, GameConfig.PLAYER_RADIUS * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (GameConfig.PLAYER_RADIUS, GameConfig.PLAYER_RADIUS), GameConfig.PLAYER_RADIUS)
        screen.blit(s, (pos.x - GameConfig.PLAYER_RADIUS, pos.y - GameConfig.PLAYER_RADIUS))

def draw_particles():
    for p in particles:
        alpha = int(255 * (p['life'] / p['max_life']))
        s = pygame.Surface((p['radius']*2, p['radius']*2), pygame.SRCALPHA)
        pygame.draw.circle(s, p['color'] + (alpha,), (int(p['radius']), int(p['radius'])), int(p['radius']))
        screen.blit(s, (p['pos'].x - p['radius'], p['pos'].y - p['radius']))

def draw_damage_texts():
    for t in damage_texts:
        alpha = int(255 * (t['life'] / t['max_life']))
        txt_surf = font.render(str(t['text']), True, Colors.DAMAGE_TEXT)
        txt_surf.set_alpha(alpha)
        screen.blit(txt_surf, (t['pos'].x, t['pos'].y))

def draw_projectiles():
    for projectile in projectiles:
        start = projectile['pos']
        end = start + pygame.Vector2(math.cos(math.radians(projectile['angle'])), math.sin(math.radians(projectile['angle']))) * 12
        color = projectile['color']
        for i, pos in enumerate(projectile['trail']):
            alpha = int(200 * (i / len(projectile['trail'])))
            size = 4 if color != Colors.GREEN else 6
            glow_color = color + (alpha,)
            pygame.draw.circle(screen, glow_color, pos, size)
        pygame.draw.line(screen, color, start, end, 3)

def draw_enemies():
    for enemy in enemies:
        pos = enemy['pos']
        r = enemy['radius']
        if enemy.get('hurt_timer',0) > 0:
            t = enemy['hurt_timer'] / enemy.get('flash_time', GameConfig.HURT_FLASH_TIME)
            t = max(0.0, min(1.0, t))
            flash_col = (int(Colors.ENEMY[0] + (255 - Colors.ENEMY[0]) * t),
                         int(Colors.ENEMY[1] + (255 - Colors.ENEMY[1]) * t),
                         int(Colors.ENEMY[2] + (255 - Colors.ENEMY[2]) * t))
            pygame.draw.circle(screen, flash_col, pos, r)
            enemy['hurt_timer'] -= dt
        else:
            pygame.draw.circle(screen, Colors.ENEMY, pos, r)

def draw_player():
    pygame.draw.circle(screen, Colors.PLAYER_DEFAULT, GameConfig.PLAYER_POSITION_Y, GameConfig.PLAYER_RADIUS)

# ===== ENHANCED UI ELEMENTS =====
def draw_enhanced_ui():
    draw_health_bar()
    draw_stamina_bar()
    draw_dash_cooldown()
    draw_game_stats()
    draw_fps_counter()  # Přidáno: FPS counter
    draw_game_state_overlay()

def draw_health_bar():
    global smooth_hp
    smooth_hp += (GameConfig.PLAYER_MAX_HEALTH - smooth_hp) * 10 * dt
    hp_percent = smooth_hp / GameConfig.PLAYER_MAX_HEALTH
    
    # Health bar background
    pygame.draw.rect(screen, Colors.UI_BG, (20, 50, 220, 22), border_radius=5)
    
    # Health bar fill with gradient
    if hp_percent > 0.6:
        color = Colors.GREEN
    elif hp_percent > 0.3:
        color = (255, 210, 0)  # Yellow-orange
    else:
        color = Colors.RED
    
    pygame.draw.rect(screen, color, (20, 50, 220 * hp_percent, 22), border_radius=5)
    
    # Health text
    hp_text = font.render(f"{int(smooth_hp)} / {GameConfig.PLAYER_MAX_HEALTH}", True, Colors.WHITE)
    screen.blit(hp_text, (25, 52))

def draw_stamina_bar():
    global smooth_st
    smooth_st += (stamina - smooth_st) * 10 * dt
    st_percent = smooth_st / GameConfig.MAX_STAMINA
    
    # Stamina bar background
    pygame.draw.rect(screen, Colors.UI_BG, (20, 80, 220, 18), border_radius=5)
    
    # Stamina bar fill
    pygame.draw.rect(screen, Colors.STAMINA, (20, 80, 220 * st_percent, 18), border_radius=5)
    
    # Stamina text
    st_text = font.render(f"Stamina: {int(stamina)}", True, Colors.WHITE)
    screen.blit(st_text, (25, 82))

def draw_dash_cooldown():
    dash_cooldown_progress = min(1.0, (current_time - last_dash_time) / GameConfig.DASH_COOLDOWN)
    
    # Dash cooldown indicator
    center_x, center_y = 50, 120
    radius = 15
    
    if dash_cooldown_progress < 1.0:
        # Background circle
        pygame.draw.circle(screen, Colors.UI_BG, (center_x, center_y), radius)
        
        # Cooldown arc
        end_angle = -math.pi/2 + 2 * math.pi * dash_cooldown_progress
        pygame.draw.arc(screen, Colors.WHITE, 
                       (center_x - radius, center_y - radius, radius * 2, radius * 2),
                       -math.pi/2, end_angle, 3)
        
        # Cooldown text
        cd_text = font.render(f"{int((1 - dash_cooldown_progress) * (GameConfig.DASH_COOLDOWN / 1000))}s", 
                            True, Colors.WHITE)
        screen.blit(cd_text, (center_x - 8, center_y - 6))
    else:
        # Ready indicator
        pygame.draw.circle(screen, Colors.GREEN, (center_x, center_y), radius)
        ready_text = font.render("D", True, Colors.WHITE)  # D for Dash
        screen.blit(ready_text, (center_x - 5, center_y - 6))

def draw_game_stats():
    stats_text = [
        f"Kills: {stats['enemies_killed']}",
        f"Accuracy: {calculate_hit_accuracy()}%",
        f"Projectiles: {stats['projectiles_fired']}",
        f"Hits: {stats['projectiles_hit']}",
        f"Collisions: {stats['player_collisions']}"
    ]
    
    for i, text in enumerate(stats_text):
        stat_surf = font.render(text, True, Colors.WHITE)
        screen.blit(stat_surf, (GameConfig.WIDTH - 200, 50 + i * 25))

def draw_fps_counter():
    if not show_fps:
        return
        
    global current_fps, fps_history
    
    # Aktualizace FPS historie
    fps_history.append(current_fps)
    if len(fps_history) > max_fps_history:
        fps_history.pop(0)
    
    # Barva podle FPS
    if current_fps >= 120:
        color = Colors.GREEN
    elif current_fps >= 60:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    
    # Hlavní FPS text
    fps_text = font.render(f"FPS: {current_fps}", True, color)
    screen.blit(fps_text, (20, 20))
    
    # Min/Max FPS
    if len(fps_history) > 0:
        min_fps = min(fps_history)
        max_fps = max(fps_history)
        min_max_text = font.render(f"Min: {min_fps} | Max: {max_fps}", True, Colors.FPS_TEXT)
        screen.blit(min_max_text, (20, 150))
    
    # Target FPS
    target_text = font.render(f"Target: {GameConfig.FPS} FPS", True, Colors.FPS_TEXT)
    screen.blit(target_text, (20, 170))
    
    # Nápověda pro vypnutí FPS
    help_text = font.render("F1: Toggle FPS Display", True, Colors.FPS_TEXT)
    screen.blit(help_text, (20, 190))

def draw_game_state_overlay():
    if current_state == GameState.PAUSED:
        # Semi-transparent overlay
        overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))
        
        # Paused text
        paused_text = large_font.render("PAUSED", True, Colors.WHITE)
        text_rect = paused_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2))
        screen.blit(paused_text, text_rect)
        
        # Instructions
        inst_text = medium_font.render("Press ESC to resume", True, Colors.WHITE)
        inst_rect = inst_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 + 50))
        screen.blit(inst_text, inst_rect)
    
    elif current_state == GameState.GAME_OVER:
        # Game over overlay
        overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 192))
        screen.blit(overlay, (0, 0))
        
        # Game over text
        game_over_text = large_font.render("GAME OVER", True, Colors.RED)
        text_rect = game_over_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 - 50))
        screen.blit(game_over_text, text_rect)
        
        # Stats summary
        stats_lines = [
            f"Enemies killed: {stats['enemies_killed']}",
            f"Accuracy: {calculate_hit_accuracy()}%",
            f"Total projectiles: {stats['projectiles_fired']}",
            f"Player collisions: {stats['player_collisions']}"
        ]
        
        for i, line in enumerate(stats_lines):
            stat_text = medium_font.render(line, True, Colors.WHITE)
            stat_rect = stat_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 + i * 30))
            screen.blit(stat_text, stat_rect)
        
        # Restart instruction
        restart_text = medium_font.render("Press R to restart", True, Colors.GREEN)
        restart_rect = restart_text.get_rect(center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 + 150))
        screen.blit(restart_text, restart_rect)

# Main game loop
while running:
    dt = clock.tick(GameConfig.FPS) / 1000
    current_time = pygame.time.get_ticks()
    current_fps = clock.get_fps()  # Získání aktuálních FPS
    
    # Handle events based on game state
    handle_game_events()
    
    if current_state == GameState.PLAYING:
        # Update game logic
        update_game_state()
    
    # Drawing
    screen.blit(background_image, (0, 0))
    
    if current_state == GameState.PLAYING:
        # Draw game objects
        draw_dash_trail()
        draw_particles()
        draw_damage_texts()
        draw_projectiles()
        draw_enemies()
        draw_player()
    
    # Always draw UI
    draw_enhanced_ui()
    
    # Draw game state overlays (paused, game over)
    draw_game_state_overlay()
    
    pygame.display.flip()

# Save stats when game ends
stats["hit_accuracy_percent"] = calculate_hit_accuracy()
with open(Path.json_save, "w") as f:
    json.dump(stats, f, indent=4)
print("Statistiky uloženy do game_stats.json")

pygame.quit()