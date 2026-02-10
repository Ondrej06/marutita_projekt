import pygame
import random

from config import MenuConfig
from visuals import update_stars, draw_stars
from states import (
    GameState,
    IntroState,
    MainMenuState,
    SettingsState,
    PlayingState,
)


# =========================================================
# METEORY
# =========================================================
class MeteorSystem:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.meteors = []

    def update(self, dt):
        if random.random() < 0.01 and len(self.meteors) < 3:
            self.meteors.append(
                {
                    "x": random.randint(0, self.width),
                    "y": 0,
                    "length": random.randint(10, 30),
                    "speed": random.uniform(500, 800),
                }
            )

        for m in self.meteors[:]:
            m["y"] += m["speed"] * dt
            if m["y"] > self.height:
                self.meteors.remove(m)

    def draw(self, surface):
        for m in self.meteors:
            pygame.draw.line(
                surface,
                (255, 255, 255),
                (m["x"], m["y"]),
                (m["x"], m["y"] + m["length"]),
                2,
            )


# =========================================================
# STATE MANAGER
# =========================================================
class StateManager:
    def __init__(self):
        self.states = {}
        self.current = None
        self.running = True

    def register(self, key, state_obj):
        self.states[key] = state_obj

    def change_state(self, key, payload=None):
        if self.current:
            self.current.exit()

        self.current = self.states.get(key)

        if self.current:
            self.current.enter(payload)

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def render(self, surface):
        if self.current:
            self.current.render(surface)


# =========================================================
# BACKGROUND CREATION
# =========================================================
def create_space_background(width, height):
    surface = pygame.Surface((width, height))

    top_color = (0, 0, 0)
    bottom_color = (20, 0, 40)

    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    nebula_colors = [(100, 0, 150), (50, 0, 100), (20, 10, 60)]
    for _ in range(5):
        pos = (random.randint(0, width), random.randint(0, height))
        radius = random.randint(150, 400)
        color = random.choice(nebula_colors)
        alpha = random.randint(30, 80)

        nebula = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            nebula, (*color, alpha), (radius, radius), radius
        )
        surface.blit(nebula, (pos[0] - radius, pos[1] - radius))

    return surface


# =========================================================
# MAIN
# =========================================================
def main():
    pygame.init()

    width = MenuConfig.MENU_SCREEN_WIDTH
    height = MenuConfig.MENU_SCREEN_HEIGHT

    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Menu")
    clock = pygame.time.Clock()

    background = create_space_background(width, height)
    meteors = MeteorSystem(width, height)

    manager = StateManager()

    intro = IntroState(manager)
    main_menu = MainMenuState(manager)
    settings = SettingsState(manager)
    playing = PlayingState(manager)

    manager.register(GameState.INTRO, intro)
    manager.register(GameState.MAIN_MENU, main_menu)
    manager.register(GameState.SETTINGS, settings)
    manager.register(GameState.PLAYING, playing)

    manager.change_state(GameState.INTRO)

    # -------------------------
    # MAIN LOOP
    # -------------------------
    while manager.running:
        dt = clock.tick(MenuConfig.MENU_FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                manager.running = False
                continue

            manager.handle_event(event)

            if (
                event.type == pygame.KEYDOWN
                and manager.current is intro
                and not intro.hyperspace
            ):
                intro.hyperspace = True
                intro.hyperspace_timer = 0.0

        hyperspace = (
            manager.current is intro and getattr(intro, "hyperspace", False)
        )

        # ---------- UPDATE ----------
        meteors.update(dt)
        update_stars(dt, hyperspace)
        manager.update(dt)

        # ---------- RENDER ----------
        screen.blit(background, (0, 0))
        meteors.draw(screen)
        draw_stars(screen, hyperspace)
        manager.render(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
