import math

import pygame

from game_object import GameObject
from settings import BUFFS, PICKUP_R, H, WHITE

_font = None


class Pickup(GameObject):
    """Төмен түсетін бонус. Кеме алғанда әсер береді."""

    def __init__(self, kind, x, y):
        super().__init__(x, y, PICKUP_R + 6)
        self.kind = kind
        self.age = 0.0

    def update(self, game, dt):
        self.y += 3
        self.age += dt
        if self.y > game.cam_y + H + 30:
            self.alive = False

    def apply(self, ship):
        ship.add_buff(self.kind)
        self.alive = False

    def draw(self, screen, cam):
        global _font
        if _font is None:
            _font = pygame.font.SysFont("arial", 26, bold=True)
        info = BUFFS[self.kind]
        pos = (int(self.x - cam[0]), int(self.y - cam[1]))
        rad = int(PICKUP_R + 3 * math.sin(self.age * 6))  # «тыныс алады»
        pygame.draw.circle(screen, (20, 20, 50), pos, rad + 4)
        pygame.draw.circle(screen, info["color"], pos, rad)
        pygame.draw.circle(screen, WHITE, pos, rad, 3)
        label = _font.render(info["letter"], True, WHITE)
        screen.blit(label, label.get_rect(center=pos))
