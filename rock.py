import math
import random

import pygame

from game_object import GameObject
from settings import KINDS, MARGIN, SPLIT_SIZE, W, H


class Rock(GameObject):
    """Құлап келе жатқан тас: қарапайым, сауытты немесе комета."""

    def __init__(self, mult, kind="normal", size=None, x=0.0, y=0.0, drift=None):
        info = KINDS[kind]
        size = size or random.randint(*info["size"])
        super().__init__(x, y, size * 0.85, hp=info["hp"])
        self.kind, self.size, self.mult = kind, size, mult
        self.points, self.drop_chance = info["points"], info["drop"]
        self.speed = random.uniform(4, 7) * mult * info["speed"]
        self.drift = drift if drift is not None else random.uniform(-1.5, 1.5)
        self.angle, self.spin = random.uniform(0, 360), random.uniform(-3, 3)
        self.shape = [random.uniform(0.7, 1.0) for _ in range(random.randint(8, 11))]

    def aim_at(self, tx, ty):
        """Комета кеме қазір тұрған жерге ұшады."""
        frames = max(1.0, (ty - self.y) / self.speed)
        self.drift = max(-6.0, min(6.0, (tx - self.x) / frames))

    def update(self, game, dt):  # override
        scale = game.time_scale
        self.y += self.speed * scale
        self.x += self.drift * scale
        self.angle += self.spin * scale
        # төмен түсіп кеткен немесе шетке ұшып кеткен тас = +1 ұпай
        if self.y > game.cam_y + H + self.size or abs(self.x - game.cam_x - W / 2) > W / 2 + 2 * MARGIN:
            self.alive = False
            game.score += 1

    def on_destroy(self, game):  # override: үлкен тас бөлшектерге ыдырайды
        if self.size < SPLIT_SIZE:
            return
        n = int(self.size * 0.6)
        for d in (-1, 1):
            game.rocks.append(Rock(self.mult, "normal", n, self.x + d * n, self.y, self.drift + 2 * d))

    def draw(self, screen, cam):  # override
        x, y = self.screen_pos(cam)
        if self.kind == "armored":  # hp азайған сайын қызарады
            fill = {3: (90, 105, 135), 2: (115, 100, 125), 1: (150, 90, 90)}[self.hp]
            edge, width = (170, 200, 240), 5
        elif self.kind == "comet":
            fill, edge, width = (200, 80, 60), (255, 200, 120), 3
            length = math.hypot(self.drift, self.speed)
            dx, dy = self.drift / length, self.speed / length  # от құйрығы ұшу бағытына қарсы
            px, py = -dy * self.size * 0.7, dx * self.size * 0.7
            tail = (x - dx * self.size * 4, y - dy * self.size * 4)
            pygame.draw.polygon(screen, (255, 140, 50), [(x + px, y + py), (x - px, y - py), tail])
        else:
            fill, edge, width = (125, 110, 100), (190, 175, 160), 3
        n = len(self.shape)
        angles = [math.radians(self.angle) + math.tau * i / n for i in range(n)]
        pts = [(x + self.size * k * math.cos(a), y + self.size * k * math.sin(a))
               for k, a in zip(self.shape, angles)]
        pygame.draw.polygon(screen, fill, pts)
        pygame.draw.polygon(screen, edge, pts, width)
