import math

import pygame

from game_object import GameObject
from settings import BULLET_R, BULLET_SPEED, W, H, WHITE


class Bullet(GameObject):
    """Кеменің оғы."""

    slowable = False  # «Баяу уақыт» бонусы әсер ете ме

    def __init__(self, x, y, vx=0.0, vy=-BULLET_SPEED, radius=BULLET_R):
        super().__init__(x, y, radius)
        self.vx, self.vy = vx, vy

    def update(self, game, dt):
        scale = game.time_scale if self.slowable else 1.0
        self.x += self.vx * scale
        self.y += self.vy * scale
        cx, cy = game.cam_x, game.cam_y
        if not (-100 <= self.x - cx <= W + 100 and -100 <= self.y - cy <= H + 100):
            self.alive = False

    def draw(self, screen, cam):
        x, y = self.screen_pos(cam)
        n = math.hypot(self.vx, self.vy)
        pygame.draw.line(screen, (255, 200, 60), (x, y), (x - self.vx / n * 18, y - self.vy / n * 18), 6)
        pygame.draw.circle(screen, (255, 255, 220), (int(x), int(y)), self.radius)


class EnemyShot(Bullet):
    """НЛО-ның оғы: баяулатуға ұшырайды, басқаша түсті."""

    slowable = True

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y, vx, vy, radius=9)

    def draw(self, screen, cam):  # draw әдісін қайта анықтау
        pos = (int(self.x - cam[0]), int(self.y - cam[1]))
        pygame.draw.circle(screen, (255, 70, 200), pos, 10)
        pygame.draw.circle(screen, WHITE, pos, 4)
