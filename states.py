import math
import pygame
import random
import requests
import json
from threading import Thread
from enum import Enum, auto

from config import MenuConfig, GameConfig
from visuals import font_cache, Colors
from button import Button
from utils import InputBox, HelperFunctions
from player import Player
from enemy import Enemy
from projectiles import Projectile
from render import Renderer
from path import Path

# ... (ostatní stavy zůstávají, pouze PlayingState nahradíme)

width, height = MenuConfig.MENU_SCREEN_WIDTH, MenuConfig.MENU_SCREEN_HEIGHT

# -------------------------
# GAME STATES
# -------------------------
class GameState(Enum):
    INTRO = auto()
    MAIN_MENU = auto()
    PLAYING = auto()
    SETTINGS = auto()
    LOGIN = auto()

# -------------------------
# BASE STATE
# -------------------------
class BaseState:
    def __init__(self, manager): 
        self.manager = manager
    def enter(self,payload=None): pass
    def exit(self): pass
    def handle_event(self,event): pass
    def update(self,dt): pass
    def render(self,surface): pass

# -------------------------
# INTRO STATE (CINEMATIC / WARP)
# -------------------------
class IntroState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)

        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0
        self.title = ""

    def enter(self, payload=None):
        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.timer > 2.0:
            self.manager.change_state(GameState.MAIN_MENU)

    def update(self, dt):
        self.timer += dt

        # hyperspace start
        if self.timer >= 4.0 and not self.hyperspace:
            self.hyperspace = True
            self.hyperspace_timer = 0.0

        if self.hyperspace:
            self.hyperspace_timer += dt
            if self.hyperspace_timer >= MenuConfig.MENU_HYPERSPACE_DURATION:
                self.manager.change_state(GameState.MAIN_MENU)

    def render(self, surface):
        center_x = width // 2
        center_y = height // 2

        title_font = font_cache.get(96)
        base_surface = title_font.render(self.title, True, (255, 255, 255))
        text_w, text_h = base_surface.get_size()

        # ---------------------
        # NORMAL STATE (pulsing)
        # ---------------------
        if not self.hyperspace:
            pulse = math.sin(self.timer * 1.5) * 20
            alpha = max(0, min(255, int(200 + pulse)))
            base_surface.set_alpha(alpha)
            surface.blit(
                base_surface,
                base_surface.get_rect(center=(center_x, center_y)),
            )

            if self.timer > 2.0:
                font = font_cache.get(24)
                hint = font.render("Press any key to skip", True, (120, 120, 120))
                surface.blit(hint, hint.get_rect(center=(center_x, height - 80)))
            return

        # ---------------------
        # HYPERSPACE WARP EFFECT
        # ---------------------
        warp_power = min(1.0, self.hyperspace_timer / 1.5)
        warp_strength = int(70 * warp_power)
        slice_h = 2  # výška pásů

        for y in range(0, text_h, slice_h):
            current_h = min(slice_h, text_h - y)
            if current_h <= 0: 
                continue

            slice_rect = pygame.Rect(0, y, text_w, current_h)
            slice_surf = base_surface.subsurface(slice_rect)

            # sinusová deformace
            offset_x = int(math.sin(y * 0.15 + self.hyperspace_timer * 25) * warp_strength)
            scale = 1 + warp_power * 0.8
            warped_slice = pygame.transform.scale(slice_surf, (int(text_w * scale), current_h))

            draw_x = center_x - warped_slice.get_width() // 2 + offset_x
            draw_y = center_y - text_h // 2 + y
            surface.blit(warped_slice, (draw_x, draw_y))

        # fade
        fade_alpha = min(255, int(self.hyperspace_timer * 180))
        fade = pygame.Surface((width, height))
        fade.fill((0, 0, 0))
        fade.set_alpha(fade_alpha)
        surface.blit(fade, (0, 0))

# -------------------------
# MAIN MENU STATE
# -------------------------
class MainMenuState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Main Menu"
        # Uložíme si základní pozice a akce pro pozdější úpravy
        self.base_buttons = [
            ("Play", (width//2, height//2-100), self.on_play),
            ("Settings", (width//2, height//2), self.on_settings),
            ("Quit", (width//2, height//2+100), self.on_quit),
            ("Login", (width//8, height//2-450), self.on_login)
        ]
        self.buttons = []  # naplníme v enter()

    def enter(self, payload=None):
        self.buttons = []
        for text, center, action in self.base_buttons:
            if text == "Login" and hasattr(self.manager, 'user_data') and self.manager.user_data:
                # Správné získání uživatelského jména z vnořeného slovníku 'user'
                user_info = self.manager.user_data.get('user', {})
                username = user_info.get('username', 'User')
                btn = Button(username, center, action=None, base_size=48)
                btn.enabled = False   # neaktivní tlačítko
            else:
                btn = Button(text, center, action, base_size=48)
            self.buttons.append(btn)

    def on_play(self):
        self.manager.change_state(GameState.PLAYING)
        return True

    def on_login(self):
        self.manager.change_state(GameState.LOGIN)
        return True

    def on_settings(self):
        self.manager.change_state(GameState.SETTINGS)
        return True

    def on_quit(self):
        self.manager.running = False
        return True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.enabled and b.rect.collidepoint(pos):  # klikáme jen na povolená tlačítka
                    b.handle_click()

    def update(self, dt):
        pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, pos)

    def render(self, surface):
        title_font = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width//2, height//4)))
        for b in self.buttons:
            b.render(surface)

# -------------------------
# PLAYING STATE
# -------------------------
class PlayingState(BaseState):
    def update(self, dt):
        self.last_dt = dt          # <--- musí být hned na začátku
        current_time = pygame.time.get_ticks()
        # ... zbytek kódu
    def __init__(self, manager):
        super().__init__(manager)
        self.base_url = "http://127.0.0.1:5000"  # URL Flask serveru
        # Zde načti prostředky, které stačí načíst jednou (např. obrázek pozadí)
        try:
            self.background_image = pygame.image.load(Path.background).convert_alpha()
            self.background_image = pygame.transform.scale(
                self.background_image,
                (GameConfig.WIDTH, GameConfig.HEIGHT)
            )
        except Exception:
            self.background_image = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT))
            self.background_image.fill((50, 50, 80))

    def enter(self, payload=None):
        """Inicializace herních objektů při vstupu do stavu."""
        self.start_time = pygame.time.get_ticks()
        self.player = Player()
        self.enemies = []
        self.projectiles = []
        self.particles = []
        self.damage_texts = []
        self.last_projectile_time = 0
        self.last_enemy_spawn_time = pygame.time.get_ticks()
        self.last_player_hit_time = 0

        self.stats = {
            "enemies_killed": 0,
            "player_collisions": 0,
            "projectiles_fired": 0,
            "projectiles_hit": 0,
        }

        # Renderer pro vykreslování UI (potřebuje screen – předáme ho při renderování)
        self.renderer = Renderer(self.manager.screen)  # screen bude k dispozici až při renderu, ale Renderer si ho ukládá

    def exit(self):
        """Při opuštění stavu uložíme statistiky."""
        self.send_stats_to_server()
        self.save_stats_to_json()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Návrat do hlavního menu
                self.manager.change_state(GameState.MAIN_MENU)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_projectile_time >= GameConfig.PROJECTILE_DELAY:
                proj = HelperFunctions.spawn_projectile_instance(self.player.pos, current_time)
                self.projectiles.append(proj)
                self.last_projectile_time = current_time
                self.stats["projectiles_fired"] += 1

    def update(self, dt):
        self.last_dt = dt
        current_time = pygame.time.get_ticks()

        # --- Pohyb hráče ---
        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)
        self.player.fly(dt, keys)
        self.player.update(dt)
        self.player.enforce_boundaries()

        if self.player.health <= 0:
            self.manager.change_state(GameState.MAIN_MENU)  # nebo GameState.GAME_OVER
            return

        # --- Spawn nepřátel ---
        if current_time - self.last_enemy_spawn_time >= GameConfig.ENEMY_SPAWN_INTERVAL:
            self.enemies.append(HelperFunctions.spawn_enemy_improved())
            self.last_enemy_spawn_time = current_time

        # --- Kolize hráč vs nepřítel ---
        for enemy in self.enemies:
            if (self.player.pos - enemy.pos).length() < (self.player.radius + enemy.radius):
                if current_time - self.last_player_hit_time > 500:
                    direction = self.player.pos - enemy.pos
                    self.player.take_damage(15, direction)
                    self.stats["player_collisions"] += 1
                    self.last_player_hit_time = current_time

        # --- Aktualizace nepřátel ---
        for enemy in self.enemies[:]:
            enemy.update(dt, self.player.pos)
            if not enemy.is_alive:
                self.particles.extend(HelperFunctions.spawn_hit_particles(
                    enemy.pos, Colors.DEATH_PARTICLES, count=20, speed=400, lifetime=0.7))
                self.enemies.remove(enemy)
                self.stats["enemies_killed"] += 1

        # --- Aktualizace projektilů a kolize s nepřáteli ---
        for proj in self.projectiles[:]:
            proj.update(dt)
            if not proj.is_alive:
                self.projectiles.remove(proj)
                continue

            for enemy in self.enemies:
                if HelperFunctions.check_collision(proj.pos, enemy.pos, proj.radius, enemy.radius):
                    # Zpracování zásahu podle typu projektilu
                    if proj.effect_type == "pierce":
                        if enemy in proj.hit_targets:
                            continue
                        proj.hit_targets.append(enemy)
                    else:
                        proj.is_alive = False

                    enemy.take_damage(proj.damage)
                    self.stats["projectiles_hit"] += 1

                    # Částice
                    self.particles.extend(HelperFunctions.spawn_hit_particles(
                        enemy.pos, Colors.HIT_PARTICLES, count=10, speed=220, lifetime=0.4))

                    # Text poškození
                    self.damage_texts.append(HelperFunctions.spawn_damage_text(
                        enemy.pos - pygame.Vector2(0, enemy.radius + 10), proj.damage))

                    # Speciální efekty
                    if proj.effect_type == "explosive":
                        for e in self.enemies:
                            if e is not enemy and e.pos.distance_to(enemy.pos) <= 50:
                                e.take_damage(proj.damage // 2)
                    elif proj.effect_type == "slow":
                        enemy.apply_slow(GameConfig.SLOW_DURATION, GameConfig.SLOW_FACTOR)
                    elif proj.effect_type == "dot":
                        enemy.apply_dot(GameConfig.DOT_DURATION, proj.damage * GameConfig.DOT_DAMAGE_FACTOR)
                    elif proj.effect_type == "heal":
                        self.player.heal(GameConfig.HIT_HEAL)

                    break  # Projektil zasáhl jednoho nepřítele (pokud není průstřelný)

        # --- Aktualizace částic ---
        for p in self.particles[:]:
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.remove(p)
            else:
                p["pos"] += p["vel"] * dt
                p["vel"] *= 1 - 3 * dt

        # --- Aktualizace textů poškození ---
        for t in self.damage_texts[:]:
            t["life"] -= dt
            if t["life"] <= 0:
                self.damage_texts.remove(t)
            else:
                t["pos"] += t["vel"] * dt
                t["vel"] *= 1 - 1.5 * dt

    def render(self, surface):
        # Vykreslení pozadí
        surface.blit(self.background_image, (0, 0))

        # Vykreslení trailu dashe (pod hráčem)
        self.player.draw_dash_trail(surface)

        # Vykreslení částic
        self.renderer.draw_particles(self.particles)

        # Vykreslení textů poškození
        self.renderer.draw_damage_texts(self.damage_texts)

        # Vykreslení projektilů
        for proj in self.projectiles:
            proj.draw(surface)

        # Vykreslení nepřátel
        for enemy in self.enemies:
            enemy.draw(surface)

        # Vykreslení hráče
        self.player.draw(surface)

        # Vykreslení UI (health, stamina, cooldown, statistiky)
        # Potřebujeme dt – můžeme ho předat jako argument, nebo použít fixní 1/60? 
        # Pro plynulé UI použijeme dt (uložíme si ho v update nebo použijeme poslední známé)
        # Zjednodušeně: v renderu nemáme dt, proto ho předáme přes instanční proměnnou
        if hasattr(self, 'last_dt'):
            dt_ui = self.last_dt
        else:
            dt_ui = 1/60  # nouzová hodnota

        self.renderer.draw_health_bar(self.player, dt_ui)
        self.renderer.draw_stamina_bar(self.player, dt_ui)
        self.renderer.draw_dash_cooldown(self.player, pygame.time.get_ticks())
        self.renderer.draw_game_stats(self.stats)
        # FPS čítač necháme na hlavní smyčce (menu), nebo ho můžeme přidat i sem
    def send_stats_to_server(self):
        """Odeslání statistik na Flask server."""
        if not hasattr(self.manager, 'user_data') or not self.manager.user_data:
            return  # uživatel není přihlášen

        user_info = self.manager.user_data.get('user', {})
        user_id = user_info.get('id')
        if not user_id:
            return

        elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0  # čas hraní v sekundách

        data = {
            "user_id": user_id,
            "enemies_killed": self.stats["enemies_killed"],
            "player_collisions": self.stats["player_collisions"],
            "projectiles_fired": self.stats["projectiles_fired"],
            "projectiles_hit": self.stats["projectiles_hit"],
            "time_played": elapsed
        }

        try:
            response = requests.post(f"{self.base_url}/api/update_stats", json=data)
            if response.status_code == 200:
                print("Statistiky uloženy na server.")
            else:
                print(f"Chyba při ukládání na server: {response.status_code}")
        except Exception as e:
            print(f"Chyba připojení k serveru: {e}")

    def save_stats_to_json(self):
        """Uložení statistik do lokálního JSON souboru (pro zálohu)."""
        stats_copy = self.stats.copy()
        stats_copy["timestamp"] = pygame.time.get_ticks()
        if hasattr(self.manager, 'user_data') and self.manager.user_data:
            user_info = self.manager.user_data.get('user', {})
            stats_copy["user_id"] = user_info.get('id')
            stats_copy["username"] = user_info.get('username')
        try:
            with open(Path.json_save, "a") as f:
                json.dump(stats_copy, f, indent=4)
                f.write("\n")
        except Exception as e:
            print("Chyba při ukládání do JSON:", e)

# -------------------------
# SETTINGS STATE
# -------------------------
class SettingsState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Settings"
        self.buttons = [
            Button("Graphics", (width//2, height//2-100), self.on_graphics),
            Button("Audio", (width//2, height//2), self.on_audio),
            Button("Back", (width//2, height//2+100), self.on_back)
        ]

    def on_graphics(self): 
        print("Graphics pressed")
        return True
    def on_audio(self): 
        print("Audio pressed")
        return True
    def on_back(self): 
        self.manager.change_state(GameState.MAIN_MENU)
        return True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos): b.handle_click()

    def update(self, dt):
        pos = pygame.mouse.get_pos()
        for b in self.buttons: b.update(dt, pos)

    def render(self, surface):
        title_font = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width//2, height//4)))
        for b in self.buttons: b.render(surface)

import requests
from threading import Thread
import pygame

class LoginState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Login Screen"
        self.base_url = "http://127.0.0.1:5000"

        input_font = font_cache.get(32)

        # Změna: místo email_box použijeme username_box
        self.username_box = InputBox(
            width // 2 - 200, height // 2 - 40,
            400, 50, input_font
        )

        self.password_box = InputBox(
            width // 2 - 200, height // 2 + 30,
            400, 50, input_font, is_password=True
        )

        self.login_button = Button(
            text="Přihlásit",
            center=(width // 2, height // 2 + 100),
            action=self.attempt_login,
            base_size=36
        )

        self.message = ""
        self.message_color = (255, 0, 0)
        self.is_loading = False

    def handle_event(self, event):
        if self.is_loading:
            return

        self.username_box.handle_event(event)   # změna
        self.password_box.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.login_button.rect.collidepoint(event.pos):
                self.login_button.handle_click()

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        self.login_button.update(dt, mouse_pos)

    def render(self, surface):
        surface.fill((30, 30, 30))

        # Nadpis
        title_font = font_cache.get(48)
        title_text = title_font.render("Přihlášení", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(width // 2, height // 4))
        surface.blit(title_text, title_rect)

        # Popisky pro input boxy
        label_font = font_cache.get(24)
        # Uživatelské jméno
        user_label = label_font.render("Uživatelské jméno:", True, (200, 200, 200))
        surface.blit(user_label, (width // 2 - 200, height // 2 - 70))
        # Heslo
        pass_label = label_font.render("Heslo:", True, (200, 200, 200))
        surface.blit(pass_label, (width // 2 - 200, height // 2))

        # Input boxy
        self.username_box.draw(surface)
        self.password_box.draw(surface)

        # Tlačítko
        self.login_button.render(surface)

        # Zpráva
        if self.message:
            msg_font = font_cache.get(24)
            msg_text = msg_font.render(self.message, True, self.message_color)
            msg_rect = msg_text.get_rect(center=(width // 2, height // 2 + 170))
            surface.blit(msg_text, msg_rect)

        if self.is_loading:
            loading_font = font_cache.get(20)
            loading_text = loading_font.render("Probíhá přihlašování...", True, (255, 255, 0))
            loading_rect = loading_text.get_rect(center=(width // 2, height // 2 + 220))
            surface.blit(loading_text, loading_rect)

    def attempt_login(self):
        username = self.username_box.text   # změna
        password = self.password_box.text

        if not username or not password:
            self.message = "Vyplňte všechna pole"
            self.message_color = (255, 0, 0)
            return

        self.is_loading = True
        self.message = "Přihlašování..."
        self.message_color = (255, 255, 0)

        Thread(target=self.send_login_request, args=(username, password)).start()

    def send_login_request(self, username, password):
        try:
            response = requests.post(
                f"{self.base_url}/api/login",
                json={"username": username, "password": password}   # změna
            )

            if response.status_code == 200:
                data = response.json()
                self.message = "Přihlášení úspěšné!"
                self.message_color = (0, 255, 0)
                self.manager.user_data = data   # ukládáme uživatelská data
                self.manager.change_state(GameState.MAIN_MENU)
            else:
                error_msg = response.json().get("error", "Neplatné přihlašovací údaje")
                self.message = error_msg
                self.message_color = (255, 0, 0)

        except requests.exceptions.ConnectionError:
            self.message = "Nelze se připojit k serveru. Je Flask spuštěný?"
            self.message_color = (255, 0, 0)
        except Exception as e:
            self.message = f"Chyba: {str(e)}"
            self.message_color = (255, 0, 0)
        finally:
            self.is_loading = False