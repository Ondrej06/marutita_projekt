"""
render.py
=========
Třída Renderer pro vykreslování herního UI (HUD) a RenderState konstanty.

Renderer vykresluje health bar, stamina bar, dash cooldown, statistiky,
FPS čítač a overlay pro pauzu/game over.

RenderState definuje stavy overlay vykreslování — záměrně odděleno od
GameState(Enum) v states.py, který řídí přechody mezi obrazovkami.
"""

import pygame
import math
from config import GameConfig
from visuals import Colors
from utils import calculate_hit_accuracy


# =============================================================================
# STAVY OVERLAY VYKRESLOVÁNÍ
# =============================================================================

class RenderState:
    """
    Konstanty stavů pro overlay vykreslování.

    Popisuje pouze to, co má Renderer zobrazit nad herní plochou.
    Nesouvisí s přechody mezi obrazovkami (ty jsou v GameState v states.py).
    """
    PLAYING   = "playing"    # Hra probíhá normálně — žádný overlay
    PAUSED    = "paused"     # Hra je pozastavena — PAUSED overlay
    GAME_OVER = "game_over"  # Hráč zemřel — GAME OVER overlay


# =============================================================================
# RENDERER
# =============================================================================

class Renderer:
    """
    Vykresluje veškeré UI prvky na herní obrazovku.

    Attributes:
        screen (pygame.Surface): Cílový povrch pro vykreslování.
        font (pygame.font.Font): Malý font (24 pt) pro statistiky a popisky.
        large_font (pygame.font.Font): Velký font (72 pt) pro overlay texty.
        medium_font (pygame.font.Font): Střední font (36 pt) pro restart text.
        smooth_hp (float): Interpolovaná hodnota zdraví pro plynulý health bar.
        smooth_st (float): Interpolovaná hodnota staminy pro plynulý stamina bar.
    """

    def __init__(self, screen: pygame.Surface):
        pygame.font.init()
        self.screen = screen

        self.font        = pygame.font.SysFont(None, 24)
        self.large_font  = pygame.font.SysFont(None, 72)
        self.medium_font = pygame.font.SysFont(None, 36)

        self.smooth_hp = 0.0
        self.smooth_st = 0.0

    # =========================================================================
    # ČÁSTICE A TEXTY POŠKOZENÍ
    # =========================================================================

    def draw_particles(self, particles: list) -> None:
        """
        Vykreslí všechny aktivní částice.

        Args:
            particles: Seznam slovníků částic z HelperFunctions.spawn_hit_particles().
        """
        for p in particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            s = pygame.Surface((p['radius'] * 2, p['radius'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s,
                p['color'] + (alpha,),
                (int(p['radius']), int(p['radius'])),
                int(p['radius'])
            )
            self.screen.blit(s, (p['pos'].x - p['radius'], p['pos'].y - p['radius']))

    def draw_damage_texts(self, damage_texts: list) -> None:
        """
        Vykreslí plovoucí texty poškození nad zasaženými nepřáteli.

        Args:
            damage_texts: Seznam slovníků textů z HelperFunctions.spawn_damage_text().
        """
        for t in damage_texts:
            alpha = int(255 * (t['life'] / t['max_life']))
            txt_surf = self.font.render(str(t['text']), True, Colors.DAMAGE_TEXT)
            txt_surf.set_alpha(alpha)
            self.screen.blit(txt_surf, (t['pos'].x, t['pos'].y))

    def draw_projectiles(self, projectiles: list) -> None:
        """
        Deleguje vykreslení každého projektilu na jeho vlastní draw() metodu.

        Args:
            projectiles: Seznam aktivních Projectile instancí.
        """
        for projectile in projectiles:
            projectile.draw(self.screen)

    # =========================================================================
    # HUD — ZDRAVÍ A STAMINA
    # =========================================================================

    def draw_health_bar(self, player, dt: float) -> None:
        """
        Vykreslí health bar hráče s plynulou interpolací.

        Barva se mění dle procentuálního zdraví:
          >60 %: zelená, 30–60 %: žlutá, <30 %: červená.

        Args:
            player: Instance Player.
            dt: Delta time pro výpočet rychlosti interpolace.
        """
        self.smooth_hp += (player.health - self.smooth_hp) * 10 * dt
        hp_percent = max(0, self.smooth_hp / player.max_health)

        pygame.draw.rect(self.screen, Colors.UI_BG, (20, 50, 220, 22), border_radius=5)

        if hp_percent > 0.6:
            color = Colors.GREEN
        elif hp_percent > 0.3:
            color = (255, 210, 0)
        else:
            color = Colors.RED

        pygame.draw.rect(
            self.screen, color,
            (20, 50, 220 * hp_percent, 22),
            border_radius=5
        )

    def draw_stamina_bar(self, player, dt: float) -> None:
        """
        Vykreslí stamina bar pod health barem.

        Args:
            player: Instance Player.
            dt: Delta time pro interpolaci.
        """
        self.smooth_st += (player.stamina - self.smooth_st) * 10 * dt
        st_percent = self.smooth_st / GameConfig.MAX_STAMINA

        pygame.draw.rect(self.screen, Colors.UI_BG, (20, 80, 220, 18), border_radius=5)
        pygame.draw.rect(
            self.screen, Colors.STAMINA,
            (20, 80, 220 * st_percent, 18),
            border_radius=5
        )

    # =========================================================================
    # HUD — DASH COOLDOWN
    # =========================================================================

    def draw_dash_cooldown(self, player, current_time: int) -> None:
        """
        Vykreslí kruhový indikátor cooldownu dashe.

        Pokud cooldown běží: tmavý kruh s obloukem pokroku + odpočet sekund.
        Pokud je dash připraven: zelený plný kruh s písmenem "D".

        Args:
            player: Instance Player.
            current_time: Aktuální pygame timestamp (ms).
        """
        dash_cooldown_progress = min(
            1.0,
            (current_time - player.last_dash_time) / GameConfig.DASH_COOLDOWN
        )
        center_x, center_y = 50, 120
        radius = 15

        if dash_cooldown_progress < 1.0:
            pygame.draw.circle(self.screen, Colors.UI_BG, (center_x, center_y), radius)

            end_angle = -math.pi / 2 + 2 * math.pi * dash_cooldown_progress
            pygame.draw.arc(
                self.screen, Colors.WHITE,
                (center_x - radius, center_y - radius, radius * 2, radius * 2),
                -math.pi / 2, end_angle,
                3
            )

            remaining_secs = int((1 - dash_cooldown_progress) * (GameConfig.DASH_COOLDOWN / 1000))
            cd_text = self.font.render(f"{remaining_secs}s", True, Colors.WHITE)
            self.screen.blit(cd_text, (center_x - 8, center_y - 6))
        else:
            pygame.draw.circle(self.screen, Colors.GREEN, (center_x, center_y), radius)
            ready_text = self.font.render("D", True, Colors.WHITE)
            self.screen.blit(ready_text, (center_x - 5, center_y - 6))

    # =========================================================================
    # HUD — STATISTIKY
    # =========================================================================

    def draw_game_stats(self, stats: dict, elapsed_time: float = 0.0) -> None:
        """
        Vykreslí herní statistiky v pravém horním rohu obrazovky.

        Args:
            stats: Slovník se statistikami aktuální hry.
            elapsed_time: Uplynulý čas hry v sekundách.
        """
        hits  = stats.get("projectiles_hit", 0)
        shots = stats.get("projectiles_fired", 0)
        accuracy = calculate_hit_accuracy(hits, shots)

        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        time_str = f"Čas: {minutes}:{seconds:02d}"

        stats_text = [
            f"Kills: {stats.get('enemies_killed', 0)}",
            f"Accuracy: {accuracy:.1f}%",
            f"Projectiles: {shots}",
            f"Hits: {hits}",
            f"Collisions: {stats.get('player_collisions', 0)}",
            time_str,
        ]

        for i, text in enumerate(stats_text):
            stat_surf = self.font.render(text, True, Colors.WHITE)
            self.screen.blit(stat_surf, (GameConfig.WIDTH - 200, 50 + i * 25))

    # =========================================================================
    # HUD — FPS ČÍTAČ
    # =========================================================================

    def draw_fps_counter(self, current_fps: float, show_fps: bool,
                         fps_history: list) -> None:
        """
        Vykreslí FPS čítač v levém horním rohu (přepínatelný klávesou F1).

        Barva: ≥60 FPS zelená, 30–59 žlutá, <30 červená.

        Args:
            current_fps: Aktuální FPS z clock.get_fps().
            show_fps: True = FPS se zobrazuje.
            fps_history: Seznam historických FPS hodnot.
        """
        if not show_fps:
            return

        fps_history.append(current_fps)
        if len(fps_history) > 100:
            fps_history.pop(0)

        if current_fps >= 60:
            color = Colors.GREEN
        elif current_fps >= 30:
            color = Colors.YELLOW
        else:
            color = Colors.RED

        fps_text = self.font.render(f"FPS: {int(current_fps)}", True, color)
        self.screen.blit(fps_text, (20, 20))

    # =========================================================================
    # OVERLAY — PAUZA A GAME OVER
    # =========================================================================

    def draw_game_overlay(self, current_state) -> None:
        """
        Vykreslí poloprůhledný overlay pro pauzu nebo game over.

        Args:
            current_state: Aktuální stav (RenderState.PAUSED nebo GAME_OVER).
        """
        if current_state == RenderState.PAUSED:
            overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            self.screen.blit(overlay, (0, 0))

            paused_text = self.large_font.render("PAUSED", True, Colors.WHITE)
            text_rect = paused_text.get_rect(
                center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2)
            )
            self.screen.blit(paused_text, text_rect)

        elif current_state == RenderState.GAME_OVER:
            overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 192))
            self.screen.blit(overlay, (0, 0))

            msg = self.large_font.render("GAME OVER", True, Colors.RED)
            msg_rect = msg.get_rect(
                center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 - 50)
            )
            self.screen.blit(msg, msg_rect)

            restart_text = self.medium_font.render("Press R to restart", True, Colors.GREEN)
            restart_rect = restart_text.get_rect(
                center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 + 150)
            )
            self.screen.blit(restart_text, restart_rect)