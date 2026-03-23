"""
states_game.py
==============
Herní stav — PlayingState.

Obsahuje veškerou herní logiku: pohyb hráče, spawn nepřátel,
detekci kolizí, aplikaci efektů projektilů, sledování statistik
a jejich odeslání na Flask server po skončení hry.

Menu stavy jsou odděleny v states_menu.py.
Sdílené základní třídy jsou v states.py.
"""

import pygame
import requests
import json
from threading import Thread

from config import GameConfig, AppConfig
from visuals import Colors
from states import BaseState, GameState
from player import Player
from render import Renderer, RenderState
from utils import HelperFunctions
from settings import JSON_SAVE


class PlayingState(BaseState):
    """
    Hlavní herní stav — obsahuje celou herní logiku.

    Zodpovídá za:
      - Inicializaci herních objektů (hráč, nepřátelé, projektily, částice).
      - Zpracování vstupu (pohyb, střelba).
      - Fyzikální simulaci a detekci kolizí.
      - Spawn nepřátel a aplikaci efektů projektilů.
      - Sledování statistik a jejich odeslání po skončení hry.

    Attributes:
        player (Player): Instance hráče.
        enemies (list): Aktivní nepřátelé.
        projectiles (list): Aktivní projektily.
        particles (list): Aktivní částice efektů.
        damage_texts (list): Aktivní plovoucí texty poškození.
        stats (dict): Statistiky aktuální hry.
        renderer (Renderer): Vykresluje HUD.
        elapsed_time (float): Uplynulý čas hry v sekundách.
        start_time (int): Pygame timestamp začátku hry (ms).
        last_dt (float): DT z posledního update() — pro render().
        game_over (bool): True = hráč zemřel, zobrazuje se Game Over overlay.
        show_fps (bool): True = zobrazuje se FPS čítač (přepínáno klávesou F1).
        fps_history (list): Historie FPS hodnot pro draw_fps_counter().
        current_fps (float): Aktuální FPS vypočítané z dt.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.base_url = AppConfig.SERVER_URL

        self.elapsed_time = 0.0
        self.last_dt = 1 / 60
        self.game_over = False
        self.show_fps = False
        self.fps_history = []
        self.current_fps = 0.0

        # Načtení obrázku pozadí — provede se jednou při inicializaci
        try:
            from settings import BACKGROUND
            self.background_image = pygame.image.load(BACKGROUND).convert_alpha()
            self.background_image = pygame.transform.scale(
                self.background_image, (GameConfig.WIDTH, GameConfig.HEIGHT)
            )
        except Exception:
            self.background_image = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT))
            self.background_image.fill((50, 50, 80))

    def enter(self, payload=None):
        """
        Inicializuje/resetuje všechny herní objekty při vstupu do hry.

        Volá se pokaždé při přechodu z menu — zajišťuje čistý stav.
        """
        self.start_time = pygame.time.get_ticks()
        self.elapsed_time = 0.0
        self.game_over = False
        self.fps_history = []
        self.current_fps = 0.0

        self.player       = Player()
        self.enemies      = []
        self.projectiles  = []
        self.particles    = []
        self.damage_texts = []

        self.last_projectile_time  = 0
        self.last_enemy_spawn_time = pygame.time.get_ticks()
        self.last_player_hit_time  = 0

        self.stats = {
            "enemies_killed":    0,
            "player_collisions": 0,
            "projectiles_fired": 0,
            "projectiles_hit":   0,
        }

        self.renderer = Renderer(self.manager.screen)

    def exit(self):
        """
        Uloží statistiky při opuštění stavu (ESC nebo smrt hráče).

        Odesílání na server běží v samostatném vlákně, aby neblokoval
        přechod zpět do menu. Do JSON se ukládá pouze při selhání serveru,
        aby nedocházelo k duplicitám při pozdějším importu.
        """
        Thread(target=self._send_and_backup, daemon=True).start()

    def _send_and_backup(self):
        """Odešle statistiky na server; při selhání uloží zálohu do JSON."""
        success = self.send_stats_to_server()
        if not success:
            self.save_stats_to_json()

    def handle_event(self, event: pygame.event.Event):
        """
        Zpracuje vstup hráče.

        ESC → návrat do menu.
        R (po Game Over) → návrat do menu.
        F1 → přepnutí FPS čítače.
        Levé tlačítko myši → výstřel (pouze pokud hra běží).
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.change_state(GameState.MAIN_MENU)
                return

            # Přepnutí FPS čítače klávesou F1
            if event.key == pygame.K_F1:
                self.show_fps = not self.show_fps
                return

            # Po Game Over: klávesa R přejde zpět do menu
            if self.game_over and event.key == pygame.K_r:
                self.manager.change_state(GameState.MAIN_MENU)
                return

        # Střelba je blokována po Game Over
        if not self.game_over:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                current_time = pygame.time.get_ticks()
                if current_time - self.last_projectile_time >= GameConfig.PROJECTILE_DELAY:
                    proj = HelperFunctions.spawn_projectile_instance(
                        self.player.pos, current_time
                    )
                    self.projectiles.append(proj)
                    self.last_projectile_time = current_time
                    self.stats["projectiles_fired"] += 1

    def update(self, dt: float):
        """
        Hlavní herní logika — volá se každý snímek.

        Pořadí:
          1. Pohyb a aktualizace hráče.
          2. Kontrola smrti hráče — přechod do Game Over stavu.
          3. Spawn nepřátel (časovač).
          4. Kolize hráč ↔ nepřátelé.
          5. Aktualizace nepřátel, odstranění mrtvých.
          6. Aktualizace projektilů, kolize s nepřáteli, aplikace efektů.
          7. Aktualizace částic a textů poškození.
        """
        self.last_dt = dt
        self.current_fps = 1.0 / dt if dt > 0 else 0.0

        # Pokud je hra ve stavu Game Over, dál se neaktualizuje herní logika
        if self.game_over:
            return

        current_time = pygame.time.get_ticks()
        self.elapsed_time = (current_time - self.start_time) / 1000.0

        # ── Hráč ──────────────────────────────────────────────────────────
        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)
        self.player.fly(dt, keys)
        self.player.update(dt)
        self.player.enforce_boundaries()

        # Místo okamžitého přechodu do menu se zobrazí Game Over overlay
        if self.player.health <= 0:
            self.player.health = 0   # Zabrání záporným hodnotám v HUD
            self.game_over = True
            return

        # ── Spawn nepřátel ────────────────────────────────────────────────
        if current_time - self.last_enemy_spawn_time >= GameConfig.ENEMY_SPAWN_INTERVAL:
            self.enemies.append(HelperFunctions.spawn_enemy_improved())
            self.last_enemy_spawn_time = current_time

        # ── Kolize hráč ↔ nepřítel (cooldown 500 ms) ─────────────────────
        for enemy in self.enemies:
            dist = (self.player.pos - enemy.pos).length()
            if dist < (self.player.radius + enemy.radius):
                if current_time - self.last_player_hit_time > 500:
                    direction = self.player.pos - enemy.pos
                    self.player.take_damage(15, direction)
                    self.stats["player_collisions"] += 1
                    self.last_player_hit_time = current_time

        # ── Aktualizace nepřátel ──────────────────────────────────────────
        for enemy in self.enemies[:]:
            enemy.update(dt, self.player.pos)
            if not enemy.is_alive:
                self.particles.extend(
                    HelperFunctions.spawn_hit_particles(
                        enemy.pos, Colors.DEATH_PARTICLES,
                        count=20, speed=400, lifetime=0.7
                    )
                )
                self.enemies.remove(enemy)
                self.stats["enemies_killed"] += 1

        # ── Aktualizace projektilů ────────────────────────────────────────
        for proj in self.projectiles[:]:
            proj.update(dt)

            if not proj.is_alive:
                self.projectiles.remove(proj)
                continue

            for enemy in self.enemies:
                if HelperFunctions.check_collision(
                    proj.pos, enemy.pos, proj.radius, enemy.radius
                ):
                    first_hit = False
                    if proj.effect_type == "pierce":
                        if enemy in proj.hit_targets:
                            continue
                        if len(proj.hit_targets) == 0:
                            first_hit = True
                        proj.hit_targets.append(enemy)
                    else:
                        proj.is_alive = False
                        first_hit = True

                    enemy.take_damage(proj.damage)

                    if first_hit:
                        self.stats["projectiles_hit"] += 1

                    self.particles.extend(
                        HelperFunctions.spawn_hit_particles(
                            enemy.pos, Colors.HIT_PARTICLES,
                            count=10, speed=220, lifetime=0.4
                        )
                    )
                    self.damage_texts.append(
                        HelperFunctions.spawn_damage_text(
                            enemy.pos - pygame.Vector2(0, enemy.radius + 10),
                            proj.damage
                        )
                    )

                    # Speciální efekty dle typu projektilu
                    if proj.effect_type == "explosive":
                        for e in self.enemies:
                            if e is not enemy and e.pos.distance_to(enemy.pos) <= 50:
                                e.take_damage(proj.damage // 2)
                    elif proj.effect_type == "slow":
                        enemy.apply_slow(GameConfig.SLOW_DURATION, GameConfig.SLOW_FACTOR)
                    elif proj.effect_type == "dot":
                        enemy.apply_dot(
                            GameConfig.DOT_DURATION,
                            proj.damage * GameConfig.DOT_DAMAGE_FACTOR
                        )
                    elif proj.effect_type == "heal":
                        self.player.heal(GameConfig.HIT_HEAL)

                    break

        # ── Aktualizace částic ────────────────────────────────────────────
        for p in self.particles[:]:
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.remove(p)
            else:
                p["pos"] += p["vel"] * dt
                p["vel"] *= 1 - 3 * dt

        # ── Aktualizace textů poškození ───────────────────────────────────
        for t in self.damage_texts[:]:
            t["life"] -= dt
            if t["life"] <= 0:
                self.damage_texts.remove(t)
            else:
                t["pos"] += t["vel"] * dt
                t["vel"] *= 1 - 1.5 * dt

    def render(self, surface: pygame.Surface):
        """
        Vykreslí celou herní scénu (painter's algorithm).

        Pořadí vrstev: pozadí → dash stopa → částice → texty →
        projektily → nepřátelé → hráč → HUD → FPS → overlay.
        """
        surface.blit(self.background_image, (0, 0))

        self.player.draw_dash_trail(surface)
        self.renderer.draw_particles(self.particles)
        self.renderer.draw_damage_texts(self.damage_texts)

        for proj in self.projectiles:
            proj.draw(surface)

        for enemy in self.enemies:
            enemy.draw(surface)

        self.player.draw(surface)

        dt_ui = self.last_dt
        self.renderer.draw_health_bar(self.player, dt_ui)
        self.renderer.draw_stamina_bar(self.player, dt_ui)
        self.renderer.draw_dash_cooldown(self.player, pygame.time.get_ticks())
        self.renderer.draw_game_stats(self.stats, self.elapsed_time)

        # FPS čítač — přepínatelný klávesou F1
        self.renderer.draw_fps_counter(self.current_fps, self.show_fps, self.fps_history)

        # Game Over overlay — zobrazí se po smrti hráče
        if self.game_over:
            self.renderer.draw_game_overlay(RenderState.GAME_OVER)

    # ── Ukládání statistik ────────────────────────────────────────────────────

    def send_stats_to_server(self) -> bool:
        """
        Odešle statistiky hry na Flask REST API (pouze přihlášený uživatel).

        Returns:
            bool: True = statistiky úspěšně uloženy na serveru,
                  False = server nedostupný nebo uživatel nepřihlášen.
        """
        if not self.manager.user_data:
            return False

        user_info = self.manager.user_data.get('user', {})
        user_id   = user_info.get('id')
        if not user_id:
            return False

        elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0

        data = {
            "user_id":           user_id,
            "enemies_killed":    self.stats["enemies_killed"],
            "player_collisions": self.stats["player_collisions"],
            "projectiles_fired": self.stats["projectiles_fired"],
            "projectiles_hit":   self.stats["projectiles_hit"],
            "time_played":       elapsed
        }

        try:
            response = requests.post(f"{self.base_url}/api/update_stats", json=data)
            if response.status_code == 200:
                print("Statistiky uloženy na server.")
                return True
            else:
                print(f"Chyba při ukládání na server: {response.status_code}")
                return False
        except Exception as e:
            print(f"Chyba připojení k serveru: {e}")
            return False

    def save_stats_to_json(self):
        """
        Záložní uložení statistik do game_stats.json (append mód).

        Záznamy s user_id/username lze importovat skriptem import_jsonDB.py.
        """
        stats_copy = self.stats.copy()
        stats_copy["timestamp"]   = pygame.time.get_ticks()
        stats_copy["time_played"] = (pygame.time.get_ticks() - self.start_time) / 1000.0

        if self.manager.user_data:
            user_info = self.manager.user_data.get('user', {})
            stats_copy["user_id"]  = user_info.get('id')
            stats_copy["username"] = user_info.get('username')

        try:
            with open(JSON_SAVE, "a") as f:
                json.dump(stats_copy, f, indent=4)
                f.write("\n")
        except Exception as e:
            print("Chyba při ukládání do JSON:", e)