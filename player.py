"""
player.py
=========
Třída Player reprezentující hráčovu postavu.

Hráč je kruhový objekt pohybující se v 2D herní ploše.
Podporuje horizontální pohyb, létání (gravitace + stamina),
dash s vizuální stopou, knockback při zásahu a dobu nezranitelnosti.
"""

import math

import pygame
from config import GameConfig
from visuals import Colors


class Player:
    """
    Hráčova postava s plnou fyzikou, pohybem a stavovým systémem.

    Attributes:
        pos (pygame.Vector2): Aktuální pozice středu hráče (px).
        velocity (pygame.Vector2): Aktuální rychlost — používá se hlavně pro osu Y (gravitace).
        health (int): Aktuální zdraví.
        max_health (int): Maximální zdraví.
        radius (int): Poloměr kolizní kružnice.
        iframe (float): Zbývající doba nezranitelnosti po zásahu (s).
                        Hráč nemůže být znovu zasažen, dokud > 0.
        knockback (pygame.Vector2): Vektor odhazovací síly aplikované při zásahu.
        dashing (bool): True = hráč právě provádí dash.
        dash_direction (int): Směr dashe: +1 vpravo, -1 vlevo, 0 = žádný.
        dash_time (float): Jak dlouho aktuální dash probíhá (s).
        last_dash_time (int): Pygame timestamp posledního dashe (ms) — pro cooldown.
        dash_trail (list): Seznam bodů [pozice, zbývající_čas, alpha] tvořících stopu.
        stamina (float): Aktuální stamina pro létání (0–MAX_STAMINA).
    """

    def __init__(self):
        """
        Inicializuje hráče uprostřed obrazovky na úrovni podlahy.
        Všechny stavy jsou v klidové výchozí hodnotě.
        """
        # Pozice: horizontální střed obrazovky, vertikálně na podlaze
        self.pos = pygame.Vector2(GameConfig.WIDTH // 2, GameConfig.GROUND_LEVEL)
        self.velocity = pygame.Vector2(0, 0)

        # Zdraví
        self.health = GameConfig.PLAYER_MAX_HEALTH
        self.max_health = GameConfig.PLAYER_MAX_HEALTH
        self.radius = GameConfig.PLAYER_RADIUS

        # Nezranitelnost a odhazování
        self.iframe = 0.0           # Sekund zbývajících do konce nezranitelnosti
        self.knockback = pygame.Vector2(0, 0)

        # Dash stav
        self.dashing = False
        self.dash_direction = 0     # +1 = vpravo, -1 = vlevo
        self.dash_time = 0          # Počitadlo délky probíhajícího dashe (s)
        self.last_dash_time = 0     # Pygame ticks posledního dashe — pro cooldown
        self.dash_trail = []        # [pygame.Vector2 pos, float life, float alpha]

        # Stamina pro létání
        self.stamina = GameConfig.MAX_STAMINA

    # =========================================================================
    # AKTUALIZACE STAVU
    # =========================================================================

    def update(self, dt: float) -> None:
        """
        Aktualizuje vedlejší stavy hráče — nezávisle na vstupu.

        Volá se každý snímek bez ohledu na stisknuté klávesy.
        Stará se o:
          - postupné odznívání knockbacku
          - odpočítání doby nezranitelnosti (iframe)
          - aktualizaci bodů dash stopy

        Args:
            dt: Delta time v sekundách od posledního snímku.
        """
        # Aplikuj knockback na pozici a pak ho tlum (exponenciální útlum)
        self.pos += self.knockback * dt
        self.knockback *= (1 - 6 * dt)  # Každou sekundu se knockback zmenší na ~1/400

        # Snižuj dobu nezranitelnosti (nesmí klesnout pod nulu)
        if self.iframe > 0:
            self.iframe -= dt

        # Aktualizuj body vizuální stopy dashe
        self.update_dash_trail(dt)

    def move(self, dt: float, keys) -> None:
        """
        Zpracuje horizontální pohyb a dash dle stisknutých kláves.

        Logika pohybu:
          - Normální pohyb: A/D posunuje hráče konstantní rychlostí.
          - Dash: CTRL + A/D spustí krátkodobý rychlý pohyb s cooldownem.
            Během dashe se normální pohyb ignoruje (polohu řídí dash logika).

        Args:
            dt: Delta time v sekundách.
            keys: Výsledek pygame.key.get_pressed() — stav všech kláves.
        """
        if not self.dashing:
            # Standardní horizontální pohyb
            if keys[pygame.K_d]:
                self.pos.x += GameConfig.PLAYER_SPEED * dt
            if keys[pygame.K_a]:
                self.pos.x -= GameConfig.PLAYER_SPEED * dt

        # ── Spuštění dashe ────────────────────────────────────────────────────
        if keys[pygame.K_LCTRL] and not self.dashing:
            current_time = pygame.time.get_ticks()
            cooldown_elapsed = current_time - self.last_dash_time

            if cooldown_elapsed >= GameConfig.DASH_COOLDOWN:
                # Urči směr dashe dle horizontální klávesy
                if keys[pygame.K_d]:
                    self.dash_direction = 1
                elif keys[pygame.K_a]:
                    self.dash_direction = -1
                else:
                    self.dash_direction = 0  # Bez směru = žádný dash

                if self.dash_direction != 0:
                    self.dashing = True
                    self.dash_time = 0
                    self.last_dash_time = current_time

        # ── Průběh dashe ─────────────────────────────────────────────────────
        if self.dashing:
            # Pohyb vysokou rychlostí v určeném směru
            self.pos.x += self.dash_direction * GameConfig.DASH_SPEED * dt
            self.dash_time += dt

            # Dash skončil po uplynutí DASH_DURATION sekund
            if self.dash_time >= GameConfig.DASH_DURATION:
                self.dashing = False

    def fly(self, dt: float, keys) -> None:
        """
        Zpracuje vertikální pohyb — létání mezerníkem a gravitaci.

        Logika:
          - Mezerník + stamina > 0: aplikuj FLY_LIFT (pohyb nahoru), odečti staminu.
          - Jinak: aplikuj gravitaci (pohyb dolů).
          - Na zemi (pos.y >= GROUND_LEVEL): regeneruj staminu.

        Args:
            dt: Delta time v sekundách.
            keys: Stav kláves z pygame.key.get_pressed().
        """
        if keys[pygame.K_SPACE] and self.stamina > 0:
            # Létání — záporná Y rychlost = pohyb nahoru
            self.velocity.y = -GameConfig.FLY_LIFT
            self.stamina -= GameConfig.STAMINA_USE * dt
            self.stamina = max(0, self.stamina)  # Stamina nesmí klesnout pod nulu
        else:
            # Gravitace — přičítá se každý snímek, takže rychlost narůstá
            self.velocity.y += GameConfig.GRAVITY * dt

            # Na zemi regeneruj staminu
            if self.pos.y >= GameConfig.GROUND_LEVEL:
                self.stamina = min(
                    GameConfig.MAX_STAMINA,
                    self.stamina + GameConfig.STAMINA_REGEN * dt
                )

        # Aplikuj vertikální rychlost na pozici
        self.pos.y += self.velocity.y * dt

    # =========================================================================
    # DASH STOPA
    # =========================================================================

    def update_dash_trail(self, dt: float) -> None:
        """
        Aktualizuje vizuální stopu za dashem.

        Každý snímek:
          1. Sníží životnost existujících bodů; mrtvé body odstraní.
          2. Pokud dash probíhá, přidá nové body podél trasy.

        Stopa se vykresluje v draw_dash_trail() jako průhledné kruhy
        s klesající alpha hodnotou (starší body jsou průhledné).

        Args:
            dt: Delta time v sekundách.
        """
        # Snižuj životnost každého bodu stopy
        for point in self.dash_trail[:]:
            point[1] -= dt
            if point[1] <= 0:
                self.dash_trail.remove(point)  # Bod expiroval

        # Přidej nové body během aktivního dashe
        if self.dashing:
            for i in range(GameConfig.DASH_TRAIL_LENGTH):
                # Každý bod je posunutý dozadu od aktuální pozice
                offset = -i * 6  # 6 px mezera mezi body stopy
                trail_pos = self.pos + pygame.Vector2(offset * self.dash_direction, 0)
                alpha = 255 * (1 - i / GameConfig.DASH_TRAIL_LENGTH)  # Vzdálenější = průhledný
                self.dash_trail.append([trail_pos, GameConfig.DASH_TRAIL_LIFETIME, alpha])

    # =========================================================================
    # VYKRESLOVÁNÍ
    # =========================================================================

    def draw(self, screen: pygame.Surface) -> None:
        """
        Vykreslí hráče jako energetický kruh s vnitřním prstencem a pulzujícím jádrem.
        """
        center = (int(self.pos.x), int(self.pos.y))
        r = self.radius

        # 1. Základní vnější záře (použijeme průhledný surface)
        glow_radius = r + 4
        glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
        # Vnější záře – světle modrá s nízkou alfa
        glow_color = (100, 150, 255, 50)
        pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
        screen.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius))

        # 2. Hlavní tělo – tmavší odstín s průhledností pro podklad
        body_color = (30, 40, 80)  # tmavě modrá
        pygame.draw.circle(screen, body_color, center, r)

        # 3. Vnitřní prstenec (kruhová výseč)
        ring_radius = r - 3
        ring_width = 3
        # Barva prstence – světle modrá
        ring_color = (80, 180, 255)
        pygame.draw.circle(screen, ring_color, center, ring_radius, ring_width)

        # 4. Pulzující jádro – velikost se mění v čase (např. podle pygame.time.get_ticks())
        # Pro jednoduchost použijeme časové proměnné, které byste měli inicializovat ve třídě
        # (např. self.last_time = pygame.time.get_ticks())
        if not hasattr(self, 'last_time'):
            self.last_time = pygame.time.get_ticks()
            self.pulse_phase = 0

        current_time = pygame.time.get_ticks()
        dt = current_time - self.last_time
        self.last_time = current_time
        self.pulse_phase += dt * 0.005  # rychlost pulzování
        # Velikost jádra se mění sinusově mezi 0.4 a 0.8 poloměru
        core_radius = int(r * (0.6 + 0.2 * (1 + math.sin(self.pulse_phase)) / 2))

        # Středové jádro – světlé, zářivé
        core_color = (200, 220, 255)
        pygame.draw.circle(screen, core_color, center, core_radius)

        # 5. Dodatečný lesklý bod (odlesk)
        highlight_radius = max(1, r // 6)
        highlight_offset = r // 3
        highlight_pos = (center[0] - highlight_offset, center[1] - highlight_offset)
        pygame.draw.circle(screen, (255, 255, 255), highlight_pos, highlight_radius)

        # 6. Obrys pro kontrast
        outline_color = (200, 200, 255)
        pygame.draw.circle(screen, outline_color, center, r, width=1)
    def draw_dash_trail(self, screen: pygame.Surface) -> None:
        """
        Vykreslí průhledné kruhy tvořící stopu za dashem.

        Každý bod stopy má svou alpha hodnotu (průhlednost),
        která klesá s ubývající životností bodu.
        Používá pygame.SRCALPHA povrch pro podporu průhlednosti.

        Args:
            screen: Cílový pygame povrch.
        """
        for point in self.dash_trail:
            pos, life, alpha = point

            # Vypočítej aktuální alpha dle zbývající životnosti bodu
            current_alpha = int(alpha * (life / GameConfig.DASH_TRAIL_LIFETIME))

            # Vytvoř malý povrch s alfa kanálem a nakresli průhledný kruh
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s,
                (*Colors.WHITE, current_alpha),
                (self.radius, self.radius),
                self.radius
            )
            screen.blit(s, (pos.x - self.radius, pos.y - self.radius))

    # =========================================================================
    # ZDRAVÍ A POŠKOZENÍ
    # =========================================================================

    def take_damage(self, damage: int, direction: pygame.Vector2) -> None:
        """
        Aplikuje poškození a knockback, pokud hráč není v době nezranitelnosti.

        Pokud iframe > 0, zásah se ignoruje — zabraňuje okamžitému opakovanému
        poškození při překryvu s nepřítelem.

        Args:
            damage: Množství HP k odečtení.
            direction: Vektor od nepřítele k hráči — určuje směr knockbacku.
        """
        if self.iframe <= 0:
            self.health -= damage
            self.iframe = 0.4  # 0.4 s nezranitelnosti po zásahu

            # Knockback: normalizovaný směr × síla odhazování
            self.knockback = direction.normalize() * 400

    def heal(self, amount: int) -> None:
        """
        Vyléčí hráče o zadaný počet HP (nepřekročí max_health).

        Volá se při zásahu žlutým (heal) projektilem.

        Args:
            amount: Počet HP k přidání.
        """
        self.health = min(self.health + amount, self.max_health)

    # =========================================================================
    # HRANICE HERNÍ PLOCHY
    # =========================================================================

    def enforce_boundaries(self) -> None:
        """
        Zabrání hráči opustit herní plochu.

        Ořízne X souřadnici na rozsah [radius, WIDTH-radius] a
        Y souřadnici maximálně na GROUND_LEVEL (nelze jít pod podlahu).
        Horní hranice Y není omezena — hráč může létat neomezeně nahoru.
        """
        self.pos.x = max(self.radius, min(GameConfig.WIDTH - self.radius, self.pos.x))
        self.pos.y = min(GameConfig.GROUND_LEVEL, self.pos.y)