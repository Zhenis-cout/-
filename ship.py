import math
import random

import pygame

from bullet import Bullet
from game_object import GameObject
from settings import BUFFS, FIRE_DELAY, MAX_LIVES, SHIP_R, WORLD_W, WORLD_H


class Ship(GameObject):
    """Ойыншының кемесі. hp = өмір саны."""

    def __init__(self, x, y):
        super().__init__(x, y, SHIP_R, hp=3)  # ата-ана конструкторын шақыру
        self.speed = 9
        self.invincible = self.cooldown = 0.0
        self.shield = False  # қалқан бір соққыны жұтады
        self.buffs = dict.fromkeys(("triple", "rapid", "slow"), 0.0)

    def has(self, kind):
        return self.buffs[kind] > 0

    def add_buff(self, kind):
        if kind == "shield":
            self.shield = True
        elif kind == "life":
            self.hp = min(MAX_LIVES, self.hp + 1)
        else:
            self.buffs[kind] = BUFFS[kind]["time"]  # қайта алса таймер жаңарады

    def update(self, game, dt):  # override
        keys = game.keys
        held = lambda *ks: any(keys[k] for k in ks)
        self.x += self.speed * (held(pygame.K_RIGHT, pygame.K_d) - held(pygame.K_LEFT, pygame.K_a))
        self.y += self.speed * (held(pygame.K_DOWN, pygame.K_s) - held(pygame.K_UP, pygame.K_w))
        self.x = max(25, min(WORLD_W - 25, self.x))
        self.y = max(40, min(WORLD_H - 40, self.y))
        self.invincible = max(0.0, self.invincible - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        for k in self.buffs:
            self.buffs[k] = max(0.0, self.buffs[k] - dt)
        if keys[pygame.K_SPACE] and self.cooldown <= 0:
            game.bullets.extend(self.shoot())

    def shoot(self):
        self.cooldown = FIRE_DELAY * (0.4 if self.has("rapid") else 1.0)
        # dx, dy, vx — бүйір оқтар «Үш ату» бонусына арналған
        pattern = [(0, -30, 0), (-14, -20, -4), (14, -20, 4)]
        count = 3 if self.has("triple") else 1
        return [Bullet(self.x + dx, self.y + dy, vx) for dx, dy, vx in pattern[:count]]

    def hit(self, damage=1):  # override: қалқан және жеңілмейтін уақыт
        if self.invincible > 0:
            return False
        if self.shield:
            self.shield, self.invincible = False, 1.0
            return False
        self.invincible = 1.5
        return super().hit(damage)

    def draw(self, screen, cam):  # override
        x, y = self.screen_pos(cam)
        if self.shield:
            pygame.draw.circle(screen, BUFFS["shield"]["color"], (int(x), int(y)),
                               int(40 + 2 * math.sin(pygame.time.get_ticks() / 120)), 3)
        if self.invincible > 0 and int(self.invincible * 10) % 2 == 0:
            return  # соққыдан кейінгі жыпылықтау
        pygame.draw.polygon(screen, (255, 150, 40),
                            [(x - 8, y + 14), (x + 8, y + 14), (x, y + 26 + random.randint(0, 14))])
        body = [(x, y - 30), (x + 22, y + 22), (x, y + 11), (x - 22, y + 22)]
        pygame.draw.polygon(screen, (90, 200, 255), body)
        pygame.draw.polygon(screen, (230, 250, 255), body, 3)
        pygame.draw.circle(screen, (20, 30, 80), (int(x), int(y - 6)), 5)
