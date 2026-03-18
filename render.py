"""
render.py
=========
Třída Renderer pro vykreslování herního UI (HUD).

Renderer je zodpovědný výhradně za vizuální výstup — neobsahuje
herní logiku. Vykresluje health bar, stamina bar, dash cooldown,
statistiky, FPS čítač a overlay pro pauzu/game over.

Plynulé UI animace jsou zajištěny exponenciální interpolací
(smooth_hp, smooth_st), která zabraňuje ostrým skokům hodnot.
"""

import pygame
import math
from config import GameConfig
from visuals import Colors
from utils import calculate_hit_accuracy, GameState


class Renderer:
    """
    Vykresluje veškeré UI prvky na herní obrazovku.

    Instanci vytvoří PlayingState při inicializaci a předává jí
    referenci na screen. Renderer si screen ukládá a používá ho
    ve všech metodách draw_*.

    Attributes:
        screen (pygame.Surface): Cílový povrch pro vykreslování.
        font (pygame.font.Font): Malý font (24 pt) pro statistiky a popisky.
        large_font (pygame.font.Font): Velký font (72 pt) pro overlay texty.
        medium_font (pygame.font.Font): Střední font (36 pt) pro restart text.
        smooth_hp (float): Interpolovaná hodnota zdraví pro plynulý health bar.
        smooth_st (float): Interpolovaná hodnota staminy pro plynulý stamina bar.
    """

    def __init__(self, screen: pygame.Surface):
        """
        Args:
            screen: Pygame povrch (hlavní herní okno).
        """
        pygame.font.init()  # Zajistí inicializaci font subsystému
        self.screen = screen

        # Systémové fonty — rychlé načtení bez externího souboru
        self.font        = pygame.font.SysFont(None, 24)   # UI text a statistiky
        self.large_font  = pygame.font.SysFont(None, 72)   # PAUSED / GAME OVER
        self.medium_font = pygame.font.SysFont(None, 36)   # "Press R to restart"

        # Interpolované hodnoty pro plynulé UI animace (lerp)
        self.smooth_hp = 0.0  # Sleduje player.health s mírným zpožděním
        self.smooth_st = 0.0  # Sleduje player.stamina s mírným zpožděním

    # =========================================================================
    # ČÁSTICE A TEXTY POŠKOZENÍ
    # =========================================================================

    def draw_particles(self, particles: list) -> None:
        """
        Vykreslí všechny aktivní částice.

        Každá částice je průhledný kruh — alpha klesá lineárně
        s ubývající životností (stárnoucí částice mizí).

        Args:
            particles: Seznam slovníků částic z HelperFunctions.spawn_hit_particles().
        """
        for p in particles:
            # Alpha: 255 = čerstvá částice, 0 = mrtvá
            alpha = int(255 * (p['life'] / p['max_life']))

            # Povrch s alfa kanálem pro průhledné vykreslení
            s = pygame.Surface((p['radius'] * 2, p['radius'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s,
                p['color'] + (alpha,),          # RGB + A
                (int(p['radius']), int(p['radius'])),
                int(p['radius'])
            )
            self.screen.blit(s, (p['pos'].x - p['radius'], p['pos'].y - p['radius']))

    def draw_damage_texts(self, damage_texts: list) -> None:
        """
        Vykreslí plovoucí texty poškození nad zasaženými nepřáteli.

        Text stoupá nahoru a průhledně mizí s ubývající životností.

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

        Smooth interpolace zabraňuje okamžitým skokům při zásahu —
        bar se plynule posouvá k aktuální hodnotě zdraví.
        Barva se mění dle procentuálního zdraví:
          - >60 %: zelená (bezpečno)
          - 30–60 %: žlutá (pozor)
          - <30 %: červená (nebezpečí)

        Args:
            player: Instance Player pro čtení health a max_health.
            dt: Delta time pro výpočet rychlosti interpolace.
        """
        # Exponenciální interpolace: faktor 10 = plynulé přiblížení za ~0.3s
        self.smooth_hp += (player.health - self.smooth_hp) * 10 * dt
        hp_percent = max(0, self.smooth_hp / player.max_health)

        # Pozadí baru (tmavý obdélník)
        pygame.draw.rect(self.screen, Colors.UI_BG, (20, 50, 220, 22), border_radius=5)

        # Barva výplně dle % zdraví
        if hp_percent > 0.6:
            color = Colors.GREEN
        elif hp_percent > 0.3:
            color = (255, 210, 0)   # Žlutá
        else:
            color = Colors.RED

        # Výplň baru — šířka odpovídá procentuálnímu zdraví
        pygame.draw.rect(
            self.screen, color,
            (20, 50, 220 * hp_percent, 22),
            border_radius=5
        )

    def draw_stamina_bar(self, player, dt: float) -> None:
        """
        Vykreslí stamina bar pod health barem.

        Args:
            player: Instance Player pro čtení staminy.
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

        Pokud cooldown stále běží: zobrazí se tmavý kruh s obloukem
        znázorňujícím pokrok a odpočet sekund uprostřed.
        Pokud je dash připraven: zelený plný kruh s písmenem "D".

        Args:
            player: Instance Player pro čtení last_dash_time.
            current_time: Aktuální pygame timestamp (ms).
        """
        # Pokrok cooldownu: 0.0 = právě použit, 1.0 = připraven
        dash_cooldown_progress = min(
            1.0,
            (current_time - player.last_dash_time) / GameConfig.DASH_COOLDOWN
        )
        center_x, center_y = 50, 120
        radius = 15

        if dash_cooldown_progress < 1.0:
            # Cooldown stále běží — tmavé pozadí + oblouk pokroku
            pygame.draw.circle(self.screen, Colors.UI_BG, (center_x, center_y), radius)

            # Oblouk: začíná od -π/2 (12 hodin) a jde po směru hodinových ručiček
            end_angle = -math.pi / 2 + 2 * math.pi * dash_cooldown_progress
            pygame.draw.arc(
                self.screen, Colors.WHITE,
                (center_x - radius, center_y - radius, radius * 2, radius * 2),
                -math.pi / 2, end_angle,
                3  # Tloušťka oblouku
            )

            # Odpočet zbývajících sekund
            remaining_secs = int((1 - dash_cooldown_progress) * (GameConfig.DASH_COOLDOWN / 1000))
            cd_text = self.font.render(f"{remaining_secs}s", True, Colors.WHITE)
            self.screen.blit(cd_text, (center_x - 8, center_y - 6))
        else:
            # Dash připraven — zelený kruh s "D"
            pygame.draw.circle(self.screen, Colors.GREEN, (center_x, center_y), radius)
            ready_text = self.font.render("D", True, Colors.WHITE)
            self.screen.blit(ready_text, (center_x - 5, center_y - 6))

    # =========================================================================
    # HUD — STATISTIKY
    # =========================================================================

    def draw_game_stats(self, stats: dict, elapsed_time: float = 0.0) -> None:
        """
        Vykreslí herní statistiky v pravém horním rohu obrazovky.

        Zobrazuje: kills, přesnost, výstřely, zásahy, kolize a uplynulý čas.

        Args:
            stats: Slovník se statistikami aktuální hry.
            elapsed_time: Uplynulý čas hry v sekundách.
        """
        hits  = stats.get("projectiles_hit", 0)
        shots = stats.get("projectiles_fired", 0)
        accuracy = calculate_hit_accuracy(hits, shots)

        # Formátování času MM:SS
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

        # Vykreslení každého řádku statistik (odsazení 25 px mezi řádky)
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

        Barva se mění dle výkonu:
          - ≥60 FPS: zelená (plynulá hra)
          - 30–59 FPS: žlutá (mírné zpomalení)
          - <30 FPS: červená (výrazné zpomalení)

        Args:
            current_fps: Aktuální FPS z clock.get_fps().
            show_fps: True = FPS se zobrazuje.
            fps_history: Seznam historických FPS hodnot (pro budoucí graf).
        """
        if not show_fps:
            return

        # Aktualizuj historii FPS (max 100 záznamů)
        fps_history.append(current_fps)
        if len(fps_history) > 100:
            fps_history.pop(0)

        # Barva dle výkonu
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

        Pauza: tmavý overlay (50 % průhlednost) + text "PAUSED".
        Game over: tmavší overlay (75 % průhlednost) + "GAME OVER" + restart instrukce.

        Args:
            current_state: Aktuální herní stav (GameState.PAUSED nebo GAME_OVER).
        """
        if current_state == GameState.PAUSED:
            # Poloprůhledné černé pozadí — zachová viditelnost herní plochy
            overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))   # Alpha 128 = 50 % průhlednost
            self.screen.blit(overlay, (0, 0))

            # Text "PAUSED" uprostřed obrazovky
            paused_text = self.large_font.render("PAUSED", True, Colors.WHITE)
            text_rect = paused_text.get_rect(
                center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2)
            )
            self.screen.blit(paused_text, text_rect)

        elif current_state == GameState.GAME_OVER:
            # Tmavší overlay pro game over — hráč je mrtvý, hra skončila
            overlay = pygame.Surface((GameConfig.WIDTH, GameConfig.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 192))   # Alpha 192 = 75 % průhlednost
            self.screen.blit(overlay, (0, 0))

            # Červený "GAME OVER" nápis
            msg = self.large_font.render("GAME OVER", True, Colors.RED)
            msg_rect = msg.get_rect(
                center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 - 50)
            )
            self.screen.blit(msg, msg_rect)

            # Instrukce pro restart (zelená = akce je dostupná)
            restart_text = self.medium_font.render("Press R to restart", True, Colors.GREEN)
            restart_rect = restart_text.get_rect(
                center=(GameConfig.WIDTH // 2, GameConfig.HEIGHT // 2 + 150)
            )
            self.screen.blit(restart_text, restart_rect)