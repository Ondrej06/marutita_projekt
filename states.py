"""
states.py
=========
Implementace všech herních stavů pomocí vzoru State Machine.

Každý stav dědí z BaseState a implementuje metody:
  - enter(payload)    — inicializace při vstupu do stavu
  - exit()            — úklid/uložení při opuštění stavu
  - handle_event(evt) — zpracování pygame událostí
  - update(dt)        — logika na každý snímek
  - render(surface)   — vykreslení stavu

Dostupné stavy:
  IntroState    — úvodní animace s hyperspace přechodem
  MainMenuState — hlavní menu s tlačítky
  PlayingState  — samotná hra (pohyb, střelba, nepřátelé)
  SettingsState — nastavení (grafika, audio)
  GraphicsState — výběr rozlišení
  LoginState    — přihlašovací formulář (komunikuje s Flask API)
"""

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
from settings import load_config, save_config

# Rozměry obrazovky z konfigurace menu
width, height = MenuConfig.MENU_SCREEN_WIDTH, MenuConfig.MENU_SCREEN_HEIGHT


# =============================================================================
# VÝČET HERNÍCH STAVŮ
# =============================================================================
class GameState(Enum):
    """
    Výčet všech možných stavů aplikace.

    Hodnoty jsou automaticky generovaná celá čísla (auto()).
    Používají se jako klíče v StateManager.states slovníku.
    """
    INTRO     = auto()   # Úvodní animace s názvem hry
    MAIN_MENU = auto()   # Hlavní menu (Play, Settings, Login, Quit)
    PLAYING   = auto()   # Aktivní hra
    SETTINGS  = auto()   # Menu nastavení
    LOGIN     = auto()   # Přihlašovací obrazovka
    GRAPHICS  = auto()   # Výběr rozlišení obrazovky


# =============================================================================
# ZÁKLADNÍ TŘÍDA STAVU
# =============================================================================
class BaseState:
    """
    Abstraktní základ pro všechny herní stavy.

    Implementuje prázdné verze všech metod — potomci přepíší
    jen ty metody, které potřebují. Díky tomu není nutné
    implementovat všechny metody v každém stavu.

    Attributes:
        manager: Reference na StateManager pro přechody mezi stavy.
    """

    def __init__(self, manager):
        """
        Args:
            manager: Instance StateManager — umožňuje volat manager.change_state().
        """
        self.manager = manager

    def enter(self, payload=None): pass   # Zavolá se při vstupu do stavu
    def exit(self):                pass   # Zavolá se při opuštění stavu
    def handle_event(self, event): pass   # Zpracování pygame událostí
    def update(self, dt):          pass   # Herní logika — každý snímek
    def render(self, surface):     pass   # Vykreslení — každý snímek


# =============================================================================
# INTRO STAV
# =============================================================================
class IntroState(BaseState):
    """
    Úvodní animace zobrazující název hry s efektem hyperspace.

    Fáze:
      1. Normální fáze (0–4 s): titulek pulzuje, hint "Press any key".
      2. Hyperspace (po 4 s nebo stisku klávesy): sinusová deformace textu,
         fade to black, přechod do MainMenu.

    Attributes:
        timer (float): Uplynulý čas od vstupu do stavu (s).
        hyperspace (bool): True = aktivní hyperspace animace.
        hyperspace_timer (float): Uplynulý čas hyperspace animace (s).
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0
        self.title = ""   # Text titulku (prázdný = pouze efekty)

    def enter(self, payload=None):
        """Resetuje všechny timery při každém vstupu."""
        self.timer = 0.0
        self.hyperspace = False
        self.hyperspace_timer = 0.0

    def handle_event(self, event: pygame.event.Event):
        """Klávesa po 2 sekundách přeskočí intro do MainMenu."""
        if event.type == pygame.KEYDOWN and self.timer > 2.0:
            self.manager.change_state(GameState.MAIN_MENU)

    def update(self, dt: float):
        """
        Aktualizuje timery a spouští hyperspace po 4 sekundách.

        Args:
            dt: Delta time v sekundách.
        """
        self.timer += dt

        # Automatické spuštění hyperspace po 4 sekundách nečinnosti
        if self.timer >= 4.0 and not self.hyperspace:
            self.hyperspace = True
            self.hyperspace_timer = 0.0

        if self.hyperspace:
            self.hyperspace_timer += dt
            # Přechod do MainMenu po dokončení hyperspace animace
            if self.hyperspace_timer >= MenuConfig.MENU_HYPERSPACE_DURATION:
                self.manager.change_state(GameState.MAIN_MENU)

    def render(self, surface: pygame.Surface):
        """
        Vykreslí titulek s pulzujícím jasem nebo hyperspace deformací.

        Normální fáze: sinusový pulz alfa hodnoty titulku.
        Hyperspace: každý řádek textu je horizontálně posunut sinusovou
        funkcí a zvětšen — simuluje warp efekt.
        """
        center_x = width // 2
        center_y = height // 2

        title_font = font_cache.get(96)
        base_surface = title_font.render(self.title, True, (255, 255, 255))
        text_w, text_h = base_surface.get_size()

        if not self.hyperspace:
            # Normální pulzující titulek
            pulse = math.sin(self.timer * 1.5) * 20
            alpha = max(0, min(255, int(200 + pulse)))
            base_surface.set_alpha(alpha)
            surface.blit(base_surface, base_surface.get_rect(center=(center_x, center_y)))

            # Hint pro přeskočení intro (zobrazí se po 2 sekundách)
            if self.timer > 2.0:
                font = font_cache.get(24)
                hint = font.render("Press any key to skip", True, (120, 120, 120))
                surface.blit(hint, hint.get_rect(center=(center_x, height - 80)))
            return

        # ── Hyperspace deformace ──────────────────────────────────────────────
        # warp_power: 0→1 během hyperspace animace (narůstá s časem)
        warp_power    = min(1.0, self.hyperspace_timer / 1.5)
        warp_strength = int(70 * warp_power)
        slice_h = 2   # Výška jednoho horizontálního pásu textu

        # Rozdělení textu na vodorovné pásy a deformace každého pásu
        for y in range(0, text_h, slice_h):
            current_h = min(slice_h, text_h - y)
            if current_h <= 0:
                continue

            slice_rect = pygame.Rect(0, y, text_w, current_h)
            slice_surf = base_surface.subsurface(slice_rect)

            # Horizontální posunutí pásu — sinusová funkce závislá na Y a čase
            offset_x = int(math.sin(y * 0.15 + self.hyperspace_timer * 25) * warp_strength)

            # Zvětšení pásu s narůstajícím warp_power
            scale = 1 + warp_power * 0.8
            warped_slice = pygame.transform.scale(slice_surf, (int(text_w * scale), current_h))

            draw_x = center_x - warped_slice.get_width() // 2 + offset_x
            draw_y = center_y - text_h // 2 + y
            surface.blit(warped_slice, (draw_x, draw_y))

        # Fade to black: alpha narůstá s časem hyperspace
        fade_alpha = min(255, int(self.hyperspace_timer * 180))
        fade = pygame.Surface((width, height))
        fade.fill((0, 0, 0))
        fade.set_alpha(fade_alpha)
        surface.blit(fade, (0, 0))


# =============================================================================
# HLAVNÍ MENU
# =============================================================================
class MainMenuState(BaseState):
    """
    Hlavní menu s tlačítky Play, Settings, Quit a Login/jméno uživatele.

    Pokud je uživatel přihlášen, tlačítko Login se nahradí jeho
    uživatelským jménem (neaktivní tlačítko jako informační prvek).

    Attributes:
        buttons (list): Aktuálně zobrazené Button instance.
        base_buttons (list): Šablona tlačítek [(text, center, action), ...].
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Main Menu"
        # Šablona tlačítek — při enter() se z ní vytvoří aktuální seznam
        self.base_buttons = [
            ("Play",     (width // 2, height // 2 - 100), self.on_play),
            ("Settings", (width // 2, height // 2),       self.on_settings),
            ("Quit",     (width // 2, height // 2 + 100), self.on_quit),
            ("Login",    (width // 8, height // 2 - 450), self.on_login),
        ]
        self.buttons = []

    def enter(self, payload=None):
        """
        Sestaví seznam tlačítek při každém vstupu do menu.

        Pokud je uživatel přihlášen (manager.user_data není None),
        tlačítko "Login" se nahradí zobrazeným jménem (disabled).
        """
        self.buttons = []
        for text, center, action in self.base_buttons:
            if text == "Login" and hasattr(self.manager, 'user_data') and self.manager.user_data:
                # Přihlášený uživatel — zobraz jeho jméno místo Login
                user_info = self.manager.user_data.get('user', {})
                username  = user_info.get('username', 'User')
                btn = Button(username, center, action=None, base_size=48)
                btn.enabled = False  # Neaktivní — pouze informace
            else:
                btn = Button(text, center, action, base_size=48)
            self.buttons.append(btn)

    # ── Akce tlačítek ────────────────────────────────────────────────────────

    def on_play(self):
        """Přejde do herního stavu."""
        self.manager.change_state(GameState.PLAYING)
        return True

    def on_login(self):
        """Přejde na přihlašovací obrazovku."""
        self.manager.change_state(GameState.LOGIN)
        return True

    def on_settings(self):
        """Přejde do nastavení."""
        self.manager.change_state(GameState.SETTINGS)
        return True

    def on_quit(self):
        """Ukončí aplikaci nastavením running = False."""
        self.manager.running = False
        return True

    def handle_event(self, event: pygame.event.Event):
        """Zpracuje klik levým tlačítkem myši na aktivní tlačítko."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.enabled and b.rect.collidepoint(pos):
                    b.handle_click()

    def update(self, dt: float):
        """Aktualizuje animační stav všech tlačítek."""
        pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, pos)

    def render(self, surface: pygame.Surface):
        """Vykreslí titulek menu a všechna tlačítka."""
        title_font    = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width // 2, height // 4)))
        for b in self.buttons:
            b.render(surface)


# =============================================================================
# HERNÍ STAV (PLAYING)
# =============================================================================
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
        last_dt (float): DT z posledního update() — pro render() bez dt parametru.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.base_url = "http://127.0.0.1:5000"  # URL Flask serveru pro API volání

        self.elapsed_time = 0.0
        self.last_dt = 1 / 60   # Nouzová hodnota (nahrazena první iterací update)

        # Načtení obrázku pozadí — provede se jednou při inicializaci
        try:
            self.background_image = pygame.image.load(Path.background).convert_alpha()
            self.background_image = pygame.transform.scale(
                self.background_image, (GameConfig.WIDTH, GameConfig.HEIGHT)
            )
        except Exception:
            # Záložní jednobarevné pozadí, pokud soubor chybí
            self.background_image = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT))
            self.background_image.fill((50, 50, 80))

    def enter(self, payload=None):
        """
        Inicializuje/resetuje všechny herní objekty při vstupu do hry.

        Volá se pokaždé, když hráč přejde z menu do hry — zajišťuje
        čistý stav bez pozůstatků z předchozí hry.
        """
        self.start_time = pygame.time.get_ticks()
        self.elapsed_time = 0.0

        # Herní objekty
        self.player      = Player()
        self.enemies     = []
        self.projectiles = []
        self.particles   = []
        self.damage_texts = []

        # Časovače událostí
        self.last_projectile_time  = 0
        self.last_enemy_spawn_time = pygame.time.get_ticks()
        self.last_player_hit_time  = 0

        # Statistiky aktuální hry (odesílají se serveru při exit())
        self.stats = {
            "enemies_killed":    0,
            "player_collisions": 0,
            "projectiles_fired": 0,
            "projectiles_hit":   0,
        }

        # Renderer potřebuje referenci na screen
        self.renderer = Renderer(self.manager.screen)

    def exit(self):
        """
        Uloží statistiky při opuštění herního stavu.

        Volá se při každém přechodu zpět do menu (ESC nebo smrt hráče).
        Odeslání serveru probíhá asynchronně (Thread), aby neblokoval UI.
        Záložní uložení do JSON je synchronní (rychlé).
        """
        self.send_stats_to_server()
        self.save_stats_to_json()

    def handle_event(self, event: pygame.event.Event):
        """
        Zpracuje vstup hráče.

        ESC → návrat do menu (automaticky zavolá exit() → uloží stats).
        Levé tlačítko myši → výstřel (s respektováním PROJECTILE_DELAY).
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.change_state(GameState.MAIN_MENU)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

        Pořadí operací:
          1. Pohyb a aktualizace hráče.
          2. Kontrola smrti hráče.
          3. Spawn nepřátel (časovač).
          4. Kolize hráč ↔ nepřátelé.
          5. Aktualizace a odstranění mrtvých nepřátel.
          6. Aktualizace projektilů a kolize s nepřáteli.
          7. Aplikace speciálních efektů projektilů.
          8. Aktualizace částic a textů poškození.

        Args:
            dt: Delta time v sekundách.
        """
        self.last_dt = dt   # Uloží pro render() (nemá vlastní dt parametr)
        current_time = pygame.time.get_ticks()
        self.elapsed_time = (current_time - self.start_time) / 1000.0

        # ── Hráč ──────────────────────────────────────────────────────────
        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)
        self.player.fly(dt, keys)
        self.player.update(dt)
        self.player.enforce_boundaries()

        # Smrt hráče → návrat do menu (exit() uloží statistiky)
        if self.player.health <= 0:
            self.manager.change_state(GameState.MAIN_MENU)
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
                # Smrt nepřítele: explozivní částice + statistika
                self.particles.extend(
                    HelperFunctions.spawn_hit_particles(
                        enemy.pos, Colors.DEATH_PARTICLES,
                        count=20, speed=400, lifetime=0.7
                    )
                )
                self.enemies.remove(enemy)
                self.stats["enemies_killed"] += 1

        # ── Aktualizace projektilů a kolize s nepřáteli ───────────────────
        for proj in self.projectiles[:]:
            proj.update(dt)

            if not proj.is_alive:
                self.projectiles.remove(proj)
                continue

            for enemy in self.enemies:
                if HelperFunctions.check_collision(
                    proj.pos, enemy.pos, proj.radius, enemy.radius
                ):
                    # Pierce typ: zkontroluj, zda tohoto nepřítele projektil ještě nezasáhl
                    first_hit = False
                    if proj.effect_type == "pierce":
                        if enemy in proj.hit_targets:
                            continue   # Tento nepřítel již byl zasažen — přeskoč
                        if len(proj.hit_targets) == 0:
                            first_hit = True
                        proj.hit_targets.append(enemy)
                    else:
                        proj.is_alive = False   # Nepiercing projektil zanikne při zásahu
                        first_hit = True

                    # Aplikace poškození
                    enemy.take_damage(proj.damage)

                    # Statistiku zvýšíme jen při prvním zásahu (ne pro každý pierce průchod)
                    if first_hit:
                        self.stats["projectiles_hit"] += 1

                    # Efektové částice a text poškození
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

                    # ── Speciální efekty dle typu projektilu ──────────────
                    if proj.effect_type == "explosive":
                        # AoE výbuch: poloviční poškození nepřátelům do 50 px
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

                    break   # Jeden projektil zasáhne max jednoho nepřítele za snímek

        # ── Aktualizace částic ────────────────────────────────────────────
        for p in self.particles[:]:
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.remove(p)
            else:
                p["pos"] += p["vel"] * dt       # Pohyb
                p["vel"] *= 1 - 3 * dt          # Zpomalení (útlum)

        # ── Aktualizace textů poškození ───────────────────────────────────
        for t in self.damage_texts[:]:
            t["life"] -= dt
            if t["life"] <= 0:
                self.damage_texts.remove(t)
            else:
                t["pos"] += t["vel"] * dt
                t["vel"] *= 1 - 1.5 * dt        # Postupné zpomalení stoupání

    def render(self, surface: pygame.Surface):
        """
        Vykreslí celou herní scénu v pořadí od nejspodnější vrstvy.

        Pořadí vrstev (painter's algorithm):
          1. Pozadí (background image)
          2. Dash stopa hráče
          3. Částice efektů
          4. Plovoucí texty poškození
          5. Projektily
          6. Nepřátelé
          7. Hráč
          8. HUD (health, stamina, dash, statistiky)

        Args:
            surface: Cílový pygame povrch.
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

        # HUD — použije last_dt z update() (render nemá vlastní dt)
        dt_ui = self.last_dt
        self.renderer.draw_health_bar(self.player, dt_ui)
        self.renderer.draw_stamina_bar(self.player, dt_ui)
        self.renderer.draw_dash_cooldown(self.player, pygame.time.get_ticks())
        self.renderer.draw_game_stats(self.stats, self.elapsed_time)

    # ── Ukládání statistik ────────────────────────────────────────────────────

    def send_stats_to_server(self):
        """
        Odešle statistiky aktuální hry na Flask REST API.

        Odesílání probíhá pouze pokud je uživatel přihlášen
        (manager.user_data obsahuje platná data s user_id).
        Chyba připojení je zachycena a tiše ignorována
        (záloha probíhá přes save_stats_to_json).
        """
        if not hasattr(self.manager, 'user_data') or not self.manager.user_data:
            return   # Nepřihlášený uživatel — neodesílej

        user_info = self.manager.user_data.get('user', {})
        user_id   = user_info.get('id')
        if not user_id:
            return

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
            else:
                print(f"Chyba při ukládání na server: {response.status_code}")
        except Exception as e:
            print(f"Chyba připojení k serveru: {e}")

    def save_stats_to_json(self):
        """
        Záložní uložení statistik do lokálního souboru game_stats.json.

        Soubor se otevírá v append módu — záznamy se přidávají za sebou.
        Při příštím startu serveru import_jsonDB.py soubor zpracuje
        a záznamy s user_id/username přenese do databáze.
        """
        stats_copy = self.stats.copy()
        stats_copy["timestamp"]  = pygame.time.get_ticks()
        stats_copy["time_played"] = (pygame.time.get_ticks() - self.start_time) / 1000.0

        # Přidej identifikaci uživatele, pokud je přihlášen
        if hasattr(self.manager, 'user_data') and self.manager.user_data:
            user_info = self.manager.user_data.get('user', {})
            stats_copy["user_id"]  = user_info.get('id')
            stats_copy["username"] = user_info.get('username')

        try:
            with open(Path.json_save, "a") as f:
                json.dump(stats_copy, f, indent=4)
                f.write("\n")   # Oddělovač mezi záznamy pro čitelnost
        except Exception as e:
            print("Chyba při ukládání do JSON:", e)


# =============================================================================
# SETTINGS STAV
# =============================================================================
class SettingsState(BaseState):
    """
    Menu nastavení s tlačítky pro grafiku, audio a návrat.

    Attributes:
        buttons (list): Tlačítka stavu.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Settings"
        self.buttons = [
            Button("Graphics", (width // 2, height // 2 - 100), self.on_graphics),
            Button("Audio",    (width // 2, height // 2),       self.on_audio),
            Button("Back",     (width // 2, height // 2 + 100), self.on_back),
        ]

    def on_graphics(self):
        """Přejde do výběru rozlišení."""
        self.manager.change_state(GameState.GRAPHICS)

    def on_audio(self):
        """Placeholder pro budoucí nastavení zvuku."""
        print("Audio pressed")
        return True

    def on_back(self):
        """Návrat do hlavního menu."""
        self.manager.change_state(GameState.MAIN_MENU)
        return True

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos):
                    b.handle_click()

    def update(self, dt: float):
        pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, pos)

    def render(self, surface: pygame.Surface):
        title_font    = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width // 2, height // 4)))
        for b in self.buttons:
            b.render(surface)


# =============================================================================
# GRAPHICS STAV (výběr rozlišení)
# =============================================================================
class GraphicsState(BaseState):
    """
    Obrazovka pro výběr rozlišení okna.

    Dostupná rozlišení jsou pevně definovaná. Výběr se okamžitě uloží
    do config.json, ale projeví se až po restartu aplikace.

    Attributes:
        resolutions (list): Seznam dostupných rozlišení [(šířka, výška), ...].
        current_resolution (tuple): Aktuálně nastavené rozlišení.
        message (str): Informační zpráva zobrazená po změně rozlišení.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title = "Graphics Settings"
        self.resolutions = [(1920, 1080), (800, 800)]
        self.current_resolution = None
        self.buttons = []
        self.message = ""

    def enter(self, payload=None):
        """Načte aktuální rozlišení z config.json a sestaví tlačítka."""
        config = load_config()
        self.current_resolution = tuple(config["resolution"])
        self.create_buttons()

    def create_buttons(self):
        """Sestaví seznam tlačítek pro každé dostupné rozlišení + tlačítko Back."""
        self.buttons = []
        y_start = height // 2 - 100
        for i, (w, h) in enumerate(self.resolutions):
            text = f"{w}x{h}"
            if (w, h) == self.current_resolution:
                text += " (aktivní)"   # Označení aktuálně nastaveného rozlišení
            btn = Button(
                text,
                (width // 2, y_start + i * 80),
                lambda res=(w, h): self.set_resolution(res)
            )
            self.buttons.append(btn)
        self.buttons.append(Button("Back", (width // 2, height // 2 + 200), self.on_back))

    def set_resolution(self, res: tuple):
        """
        Uloží nové rozlišení do config.json a obnoví tlačítka.

        Změna se projeví až po restartu aplikace.

        Args:
            res: Nové rozlišení jako (šířka, výška).
        """
        config = load_config()
        config["resolution"] = list(res)
        save_config(config)
        self.message = f"Rozlišení nastaveno na {res[0]}x{res[1]}. Restartujte hru pro uplatnění."
        self.current_resolution = res
        self.create_buttons()   # Obnov tlačítka — aktualizuje označení "(aktivní)"

    def on_back(self):
        self.manager.change_state(GameState.SETTINGS)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for b in self.buttons:
                if b.rect.collidepoint(pos):
                    b.handle_click()

    def update(self, dt: float):
        pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, pos)

    def render(self, surface: pygame.Surface):
        title_font    = font_cache.get(72)
        title_surface = title_font.render(self.title, True, (255, 255, 255))
        surface.blit(title_surface, title_surface.get_rect(center=(width // 2, height // 4)))

        for b in self.buttons:
            b.render(surface)

        # Informační zpráva o změně rozlišení
        if self.message:
            msg_font    = font_cache.get(24)
            msg_surface = msg_font.render(self.message, True, (255, 255, 0))
            surface.blit(msg_surface, msg_surface.get_rect(center=(width // 2, height // 2 + 300)))


# =============================================================================
# LOGIN STAV
# =============================================================================
class LoginState(BaseState):
    """
    Přihlašovací obrazovka pro připojení k Flask serveru.

    Přihlašovací požadavek běží v samostatném vlákně (Thread),
    aby neblokoval herní smyčku během čekání na odpověď serveru.
    Po úspěšném přihlášení se uloží username do config.json pro
    předvyplnění při příštím spuštění.

    Attributes:
        username_box (InputBox): Vstupní pole pro uživatelské jméno.
        password_box (InputBox): Vstupní pole pro heslo (maskované).
        login_button (Button): Tlačítko pro odeslání přihlášení.
        back_button (Button): Tlačítko pro návrat do menu.
        message (str): Stavová zpráva (chyba / úspěch).
        message_color (tuple): RGB barva zprávy (červená = chyba, zelená = OK).
        is_loading (bool): True = čeká se na odpověď serveru — vstup je blokován.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.title    = "Login Screen"
        self.base_url = "http://127.0.0.1:5000"

        input_font = font_cache.get(32)

        # Vstupní pole pro přihlašovací údaje
        self.username_box = InputBox(
            width // 2 - 200, height // 2 - 40,
            400, 50, input_font
        )
        self.password_box = InputBox(
            width // 2 - 200, height // 2 + 30,
            400, 50, input_font, is_password=True   # Zobrazí hvězdičky místo textu
        )

        # Tlačítka
        self.login_button = Button(
            "Přihlásit", (width // 2, height // 2 + 100),
            action=self.attempt_login, base_size=36
        )
        self.back_button = Button(
            "Zpět", (width // 2, height // 2 + 170),
            action=self.go_back, base_size=30
        )

        self.message       = ""
        self.message_color = (255, 0, 0)
        self.is_loading    = False

    def enter(self, payload=None):
        """
        Při vstupu předvyplní username posledním přihlášeným uživatelem.

        Hodnota se načte z config.json (klíč 'last_user').
        """
        config    = load_config()
        last_user = config.get("last_user")
        if last_user:
            self.username_box.text = last_user

    def go_back(self):
        """Návrat do hlavního menu bez přihlášení."""
        self.manager.change_state(GameState.MAIN_MENU)

    def handle_event(self, event: pygame.event.Event):
        """
        Zpracuje vstupy — blokuje je během načítání (is_loading=True).

        Args:
            event: Pygame událost.
        """
        if self.is_loading:
            return   # Během čekání na server nezpracovávej vstupy

        self.username_box.handle_event(event)
        self.password_box.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            if self.login_button.rect.collidepoint(pos):
                self.login_button.handle_click()
            elif self.back_button.rect.collidepoint(pos):
                self.back_button.handle_click()

    def update(self, dt: float):
        mouse_pos = pygame.mouse.get_pos()
        self.login_button.update(dt, mouse_pos)
        self.back_button.update(dt, mouse_pos)

    def render(self, surface: pygame.Surface):
        """Vykreslí přihlašovací formulář s popisky, inputy a zprávami."""
        surface.fill((30, 30, 30))   # Tmavé pozadí pro kontrast s menu

        # Nadpis
        title_font = font_cache.get(48)
        title_text = title_font.render("Přihlášení", True, (255, 255, 255))
        surface.blit(title_text, title_text.get_rect(center=(width // 2, height // 4)))

        # Popisky vstupních polí
        label_font = font_cache.get(24)
        surface.blit(
            label_font.render("Uživatelské jméno:", True, (200, 200, 200)),
            (width // 2 - 200, height // 2 - 70)
        )
        surface.blit(
            label_font.render("Heslo:", True, (200, 200, 200)),
            (width // 2 - 200, height // 2)
        )

        # Vstupní pole a tlačítka
        self.username_box.draw(surface)
        self.password_box.draw(surface)
        self.login_button.render(surface)
        self.back_button.render(surface)

        # Stavová zpráva (chyba / úspěch)
        if self.message:
            msg_font = font_cache.get(24)
            msg_text = msg_font.render(self.message, True, self.message_color)
            surface.blit(msg_text, msg_text.get_rect(center=(width // 2, height // 2 + 220)))

        # Indikátor načítání
        if self.is_loading:
            loading_font = font_cache.get(20)
            loading_text = loading_font.render("Probíhá přihlašování...", True, (255, 255, 0))
            surface.blit(loading_text, loading_text.get_rect(center=(width // 2, height // 2 + 260)))

    def attempt_login(self):
        """
        Spustí přihlašovací proces.

        Validuje vyplnění polí, nastaví loading stav a spustí
        HTTP požadavek v samostatném vlákně (Thread), aby neblokoval UI.
        """
        username = self.username_box.text
        password = self.password_box.text

        if not username or not password:
            self.message       = "Vyplňte všechna pole"
            self.message_color = (255, 0, 0)
            return

        self.is_loading    = True
        self.message       = "Přihlašování..."
        self.message_color = (255, 255, 0)

        # Spuštění v samostatném vlákně — nezablokuje herní smyčku
        Thread(target=self.send_login_request, args=(username, password)).start()

    def send_login_request(self, username: str, password: str):
        """
        Odešle přihlašovací POST požadavek na Flask API.

        Spouští se v samostatném vlákně z attempt_login().
        Po dokončení aktualizuje message a případně přejde do MainMenu.

        Args:
            username: Zadané přihlašovací jméno.
            password: Zadané heslo (nešifrované — Flask ověří bcrypt hash).
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.message       = "Přihlášení úspěšné!"
                self.message_color = (0, 255, 0)

                # Uložení dat přihlášeného uživatele do StateManageru
                self.manager.user_data = data

                # Uložení username pro předvyplnění při příštím spuštění
                config = load_config()
                config["last_user"] = data["user"]["username"]
                save_config(config)

                # Přechod do hlavního menu
                self.manager.change_state(GameState.MAIN_MENU)

            else:
                error_msg          = response.json().get("error", "Neplatné přihlašovací údaje")
                self.message       = error_msg
                self.message_color = (255, 0, 0)

        except requests.exceptions.ConnectionError:
            self.message       = "Nelze se připojit k serveru. Je Flask spuštěný?"
            self.message_color = (255, 0, 0)
        except Exception as e:
            self.message       = f"Chyba: {str(e)}"
            self.message_color = (255, 0, 0)
        finally:
            self.is_loading = False   # Vždy odblokuj UI po dokončení požadavku