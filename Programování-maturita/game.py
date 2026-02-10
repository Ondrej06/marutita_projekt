import pygame
import json

from config import GameConfig
from visuals import Colors
from path import Path
from enemy import Enemy
from player import Player
from projectiles import Projectile
from utils import GameState, HelperFunctions
from render import Renderer


def main():
    pygame.init()

    screen = pygame.display.set_mode((GameConfig.WIDTH, GameConfig.HEIGHT))
    pygame.display.set_caption("Projectile Combat Game")
    clock = pygame.time.Clock()

    running = True
    current_state = GameState.PLAYING

    show_fps = True
    fps_history = []

    # ===== POZADÍ =====
    try:
        background_image = pygame.image.load(Path.background).convert_alpha()
        background_image = pygame.transform.scale(
            background_image,
            (GameConfig.WIDTH, GameConfig.HEIGHT)
        )
    except Exception as e:
        print("Background load error:", e)
        background_image = pygame.Surface(
            (GameConfig.WIDTH, GameConfig.HEIGHT)
        )
        background_image.fill((50, 50, 80))

    # ===== OBJEKTY =====
    player = Player()
    enemies = []
    projectiles = []
    particles = []
    damage_texts = []

    renderer = Renderer(screen)

    # ===== ČASOVAČE =====
    last_projectile_time = 0
    last_enemy_spawn_time = pygame.time.get_ticks()
    last_player_hit_time = 0

    # ===== STATISTIKY =====
    stats = {
        "enemies_killed": 0,
        "player_collisions": 0,
        "projectiles_fired": 0,
        "projectiles_hit": 0,
    }

    # ===== HLAVNÍ SMYČKA =====
    while running:
        dt = clock.tick(GameConfig.FPS) / 1000
        current_time = pygame.time.get_ticks()
        current_fps = clock.get_fps()

        # ===== EVENTY =====
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_state = (
                        GameState.PAUSED
                        if current_state == GameState.PLAYING
                        else GameState.PLAYING
                    )

                elif event.key == pygame.K_r and current_state == GameState.GAME_OVER:
                    player = Player()
                    enemies.clear()
                    projectiles.clear()
                    particles.clear()
                    damage_texts.clear()

                    stats = {
                        "enemies_killed": 0,
                        "player_collisions": 0,
                        "projectiles_fired": 0,
                        "projectiles_hit": 0,
                    }

                    current_state = GameState.PLAYING

                elif event.key == pygame.K_F1:
                    show_fps = not show_fps

            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and current_state == GameState.PLAYING
            ):
                if current_time - last_projectile_time >= GameConfig.PROJECTILE_DELAY:
                    projectile = HelperFunctions.spawn_projectile_instance(
                        player.pos, current_time
                    )
                    projectiles.append(projectile)
                    last_projectile_time = current_time
                    stats["projectiles_fired"] += 1

        # ===== UPDATE =====
        if current_state == GameState.PLAYING:
            keys = pygame.key.get_pressed()

            player.move(dt, keys)
            player.fly(dt, keys)
            player.update(dt)
            player.enforce_boundaries()

            if player.health <= 0:
                current_state = GameState.GAME_OVER

            # Spawn enemy
            if current_time - last_enemy_spawn_time >= GameConfig.ENEMY_SPAWN_INTERVAL:
                enemies.append(HelperFunctions.spawn_enemy_improved())
                last_enemy_spawn_time = current_time

            # Kolize hráč vs enemy (s cooldownem)
            for enemy in enemies:
                if (player.pos - enemy.pos).length() < (
                    player.radius + enemy.radius
                ):
                    if current_time - last_player_hit_time > 500:
                        direction = player.pos - enemy.pos
                        player.take_damage(15, direction)
                        stats["player_collisions"] += 1
                        last_player_hit_time = current_time

            # Enemies
            for enemy in enemies[:]:
                enemy.update(dt, player.pos)

                if not enemy.is_alive:
                    particles.extend(
                        HelperFunctions.spawn_hit_particles(
                            enemy.pos,
                            Colors.DEATH_PARTICLES,
                            count=20,
                            speed=400,
                            lifetime=0.7,
                        )
                    )
                    enemies.remove(enemy)
                    stats["enemies_killed"] += 1

            # Projectiles
            for projectile in projectiles[:]:
                projectile.update(dt)

                if not projectile.is_alive:
                    projectiles.remove(projectile)
                    continue

                for enemy in enemies:
                    if HelperFunctions.check_collision(
                        projectile.pos,
                        enemy.pos,
                        projectile.radius,
                        enemy.radius,
                    ):
                        if projectile.effect_type == "pierce":
                            if enemy in projectile.hit_targets:
                                continue
                            projectile.hit_targets.append(enemy)
                        else:
                            projectile.is_alive = False

                        enemy.take_damage(projectile.damage)
                        stats["projectiles_hit"] += 1

                        particles.extend(
                            HelperFunctions.spawn_hit_particles(
                                enemy.pos,
                                Colors.HIT_PARTICLES,
                                count=10,
                                speed=220,
                                lifetime=0.4,
                            )
                        )

                        damage_texts.append(
                            HelperFunctions.spawn_damage_text(
                                enemy.pos
                                - pygame.Vector2(0, enemy.radius + 10),
                                projectile.damage,
                            )
                        )

                        # Speciální efekty
                        if projectile.effect_type == "explosive":
                            for e in enemies:
                                if (
                                    e is not enemy
                                    and e.pos.distance_to(enemy.pos) <= 50
                                ):
                                    e.take_damage(projectile.damage // 2)

                        elif projectile.effect_type == "slow":
                            enemy.apply_slow(
                                GameConfig.SLOW_DURATION,
                                GameConfig.SLOW_FACTOR,
                            )

                        elif projectile.effect_type == "dot":
                            enemy.apply_dot(
                                GameConfig.DOT_DURATION,
                                projectile.damage
                                * GameConfig.DOT_DAMAGE_FACTOR,
                            )

                        elif projectile.effect_type == "heal":
                            player.heal(GameConfig.HIT_HEAL)

                        break

            # Particles
            for p in particles[:]:
                p["life"] -= dt
                if p["life"] <= 0:
                    particles.remove(p)
                else:
                    p["pos"] += p["vel"] * dt
                    p["vel"] *= 1 - 3 * dt

            # Damage texts
            for t in damage_texts[:]:
                t["life"] -= dt
                if t["life"] <= 0:
                    damage_texts.remove(t)
                else:
                    t["pos"] += t["vel"] * dt
                    t["vel"] *= 1 - 1.5 * dt

        # ===== RENDER =====
        screen.blit(background_image, (0, 0))

        if current_state == GameState.PLAYING:
            player.draw_dash_trail(screen)
            renderer.draw_particles(particles)
            renderer.draw_damage_texts(damage_texts)
            renderer.draw_projectiles(projectiles)

            for enemy in enemies:
                enemy.draw(screen)

            player.draw(screen)

        fps_history.append(current_fps)
        if len(fps_history) > 60:
            fps_history.pop(0)

        renderer.draw_health_bar(player, dt)
        renderer.draw_stamina_bar(player, dt)
        renderer.draw_dash_cooldown(player, current_time)
        renderer.draw_game_stats(stats)
        renderer.draw_fps_counter(current_fps, show_fps, fps_history)
        renderer.draw_game_overlay(current_state)

        pygame.display.flip()

    # ===== SAVE STATS =====
    stats["hit_accuracy_percent"] = HelperFunctions.calculate_accuracy(stats)

    try:
        with open(Path.json_save, "w") as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        print("Stat save error:", e)

    pygame.quit()


if __name__ == "__main__":
    main()
