import math
import random
from types import SimpleNamespace as N

import pygame

pygame.init()
W, H = 1920, 1080              # окно
WORLD_W, WORLD_H = 3840, 2160  # карта: вдвое больше окна по каждой стороне
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Тастардан жалтар!")
clock = pygame.time.Clock()
font, small_font, big_font = (pygame.font.SysFont("arial", s, bold=True) for s in (36, 26, 90))
WHITE = (255, 255, 255)

FIRE_DELAY, SPLIT_SIZE, MAX_LIVES = 0.18, 34, 5  # пауза между выстрелами; камни ≥ SPLIT_SIZE раскалываются
BULLET_SPEED, BULLET_R, SHIP_R, PICKUP_R = 22, 5, 16, 20
SHOT_SPEED, MARGIN = 9, 300  # скорость выстрелов НЛО; камни появляются на MARGIN px шире окна
cx = cy = 0                  # камера: левый верхний угол окна в координатах карты

# time — сколько секунд действует (0 = до первого удара), weight — частота выпадения
BUFFS = {
    "triple": {"letter": "3", "color": (255, 160, 40), "name": "Үш ату", "time": 10, "weight": 3},
    "rapid": {"letter": "R", "color": (255, 90, 90), "name": "Жылдам ату", "time": 8, "weight": 3},
    "shield": {"letter": "S", "color": (80, 170, 255), "name": "Қалқан", "time": 0, "weight": 2},
    "slow": {"letter": "Z", "color": (170, 120, 255), "name": "Баяу уақыт", "time": 6, "weight": 2},
    "life": {"letter": "+", "color": (90, 230, 120), "name": "Өмір +1", "time": 0, "weight": 1},
}
# size — диапазон размера, speed — множитель скорости, hp — попаданий до разрушения,
# points — очки, drop — шанс выпадения бафа
KINDS = {
    "normal": dict(size=(22, 50), speed=1.0, hp=1, points=1, drop=0.08),
    "armored": dict(size=(50, 64), speed=0.7, hp=3, points=5, drop=0.6),
    "comet": dict(size=(16, 24), speed=1.8, hp=1, points=3, drop=0.2),
    "ufo": dict(hp=10, points=15, drop=1.0),  # НЛО всегда роняет баф
}


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


class Ship:
    def __init__(self, x, y):
        self.x, self.y, self.speed = x, y, 9
        self.invincible = self.cooldown = 0.0
        self.shield = False  # щит поглощает один удар
        self.buffs = dict.fromkeys(("triple", "rapid", "slow"), 0.0)  # оставшееся время бафов

    def has(self, kind):
        return self.buffs[kind] > 0

    def add_buff(self, kind):
        if kind == "shield":
            self.shield = True
        else:
            self.buffs[kind] = BUFFS[kind]["time"]  # повторный подбор обновляет таймер

    def update(self, keys, dt):
        held = lambda *ks: any(keys[k] for k in ks)
        self.x += self.speed * (held(pygame.K_RIGHT, pygame.K_d) - held(pygame.K_LEFT, pygame.K_a))
        self.y += self.speed * (held(pygame.K_DOWN, pygame.K_s) - held(pygame.K_UP, pygame.K_w))
        self.x, self.y = max(25, min(WORLD_W - 25, self.x)), max(40, min(WORLD_H - 40, self.y))
        self.invincible, self.cooldown = max(0.0, self.invincible - dt), max(0.0, self.cooldown - dt)
        for k in self.buffs:
            self.buffs[k] = max(0.0, self.buffs[k] - dt)

    def shoot(self):
        self.cooldown = FIRE_DELAY * (0.4 if self.has("rapid") else 1.0)
        shots = [(0, -30, 0), (-14, -20, -4), (14, -20, 4)]  # dx, dy, vx (боковые — для баффа «Үш ату»)
        return [N(x=self.x + dx, y=self.y + dy, vx=vx) for dx, dy, vx in shots[:3 if self.has("triple") else 1]]

    def draw(self):
        x, y = self.x - cx, self.y - cy
        if self.shield:
            pygame.draw.circle(screen, BUFFS["shield"]["color"], (int(x), int(y)),
                               int(40 + 2 * math.sin(pygame.time.get_ticks() / 120)), 3)
        if self.invincible > 0 and int(self.invincible * 10) % 2 == 0:
            return  # мигание после удара
        pygame.draw.polygon(screen, (255, 150, 40),
                            [(x - 8, y + 14), (x + 8, y + 14), (x, y + 26 + random.randint(0, 14))])
        body = [(x, y - 30), (x + 22, y + 22), (x, y + 11), (x - 22, y + 22)]
        pygame.draw.polygon(screen, (90, 200, 255), body)
        pygame.draw.polygon(screen, (230, 250, 255), body, 3)
        pygame.draw.circle(screen, (20, 30, 80), (int(x), int(y - 6)), 5)


class Rock:
    def __init__(self, mult, size=None, x=None, y=None, drift=None, kind="normal"):
        k = KINDS[kind]
        self.kind, self.hp = kind, k["hp"]
        self.size = size or random.randint(*k["size"])
        self.hit = self.size * 0.85  # радиус столкновения
        self.x = x if x is not None else random.randint(self.size, WORLD_W - self.size)
        self.y = y if y is not None else -self.size
        self.speed = random.uniform(4, 7) * mult * k["speed"]
        self.drift = drift if drift is not None else random.uniform(-1.5, 1.5)
        self.angle, self.spin = random.uniform(0, 360), random.uniform(-3, 3)
        self.shape = [random.uniform(0.7, 1.0) for _ in range(random.randint(8, 11))]

    def aim_at(self, tx, ty):  # комета летит туда, где сейчас корабль
        frames = max(1.0, (ty - self.y) / self.speed)
        self.drift = max(-6.0, min(6.0, (tx - self.x) / frames))

    def update(self, scale):
        self.y += self.speed * scale
        self.x += self.drift * scale
        self.angle += self.spin * scale

    def split(self, mult):  # осколки; мелкие камни просто исчезают
        n = int(self.size * 0.6)
        return [Rock(mult, n, self.x + d * n, self.y, self.drift + 2 * d) for d in (-1, 1) if self.size >= SPLIT_SIZE]

    def draw(self):
        x, y = self.x - cx, self.y - cy
        if self.kind == "armored":  # чем меньше hp, тем краснее
            fill, edge, width = {3: (90, 105, 135), 2: (115, 100, 125), 1: (150, 90, 90)}[self.hp], (170, 200, 240), 5
        elif self.kind == "comet":
            fill, edge, width = (200, 80, 60), (255, 200, 120), 3
            length = math.hypot(self.drift, self.speed)
            dx, dy = self.drift / length, self.speed / length  # огненный хвост назад от направления полёта
            px, py = -dy * self.size * 0.7, dx * self.size * 0.7
            tail = (x - dx * self.size * 4, y - dy * self.size * 4)
            pygame.draw.polygon(screen, (255, 140, 50), [(x + px, y + py), (x - px, y - py), tail])
        else:
            fill, edge, width = (125, 110, 100), (190, 175, 160), 3
        n = len(self.shape)
        angles = [math.radians(self.angle) + math.tau * i / n for i in range(n)]
        pts = [(x + self.size * k * math.cos(a), y + self.size * k * math.sin(a)) for k, a in zip(self.shape, angles)]
        pygame.draw.polygon(screen, fill, pts)
        pygame.draw.polygon(screen, edge, pts, width)


class UFO:
    """Парит над кораблём, стреляет в него и через 20 с улетает."""
    kind, hit, LIFE = "ufo", 42, 20

    def __init__(self, x, y):
        self.x, self.y, self.hp = x, y, KINDS["ufo"]["hp"]
        self.age, self.fire = 0.0, 1.5  # возраст; секунд до выстрела

    def update(self, ship, dt, scale):
        self.age += dt * scale
        self.fire -= dt * scale
        leaving = self.age > self.LIFE - 3  # последние 3 с — улетает вверх и не стреляет
        tx = max(60, min(WORLD_W - 60, ship.x + 350 * math.sin(self.age)))  # покачивается над кораблём
        ty = -300 if leaving else (ship.y - 320 if ship.y >= 400 else ship.y + 320)
        self.x += max(-7, min(7, (tx - self.x) * 0.04)) * scale
        self.y += (ty - self.y) * 0.03 * scale
        if self.fire <= 0 and not leaving:
            self.fire = 1.4
            d = math.hypot(ship.x - self.x, ship.y - self.y) or 1
            return N(x=self.x, y=self.y + 20, hit=9,
                     vx=(ship.x - self.x) / d * SHOT_SPEED, vy=(ship.y - self.y) / d * SHOT_SPEED)

    def split(self, mult):
        return []

    def draw(self):
        x, y = int(self.x - cx), int(self.y - cy)
        pygame.draw.ellipse(screen, (110, 230, 190), (x - 20, y - 28, 40, 34))  # купол
        pygame.draw.ellipse(screen, (150, 160, 185), (x - 44, y - 8, 88, 28))   # корпус
        pygame.draw.ellipse(screen, (220, 235, 255), (x - 44, y - 8, 88, 28), 3)
        blink = pygame.time.get_ticks() // 250
        for i, dx in enumerate((-28, 0, 28)):
            pygame.draw.circle(screen, (255, 230, 90) if (blink + i) % 2 else (255, 120, 60), (x + dx, y + 8), 4)
        pygame.draw.rect(screen, (90, 20, 20), (x - 30, y - 46, 60, 6))  # полоска жизней
        pygame.draw.rect(screen, (255, 90, 90), (x - 30, y - 46, int(60 * self.hp / KINDS["ufo"]["hp"]), 6))


def text(f, s, pos, color=WHITE):
    screen.blit(f.render(s, True, (0, 0, 0)), (pos[0] + 2, pos[1] + 2))
    screen.blit(f.render(s, True, color), pos)


def center(f, s, y, color=WHITE):
    text(f, s, ((W - f.size(s)[0]) // 2, y), color)


def minimap(g):
    ox, oy, k = W - 260, H - 155, 240 / WORLD_W
    m = lambda x, y: (int(ox + x * k), int(oy + y * k))
    pygame.draw.rect(screen, (20, 20, 60), (ox, oy, 240, 135))
    pygame.draw.rect(screen, (255, 220, 60), (ox, oy, 240, 135), 2)
    pygame.draw.rect(screen, (150, 150, 200), (*m(cx, cy), int(W * k), int(H * k)), 1)  # что видно в окне
    for p in g.pups:
        pygame.draw.circle(screen, BUFFS[p.kind]["color"], m(p.x, p.y), 3)
    for u in g.ufos:
        pygame.draw.circle(screen, (255, 80, 80), m(u.x, u.y), 4)
    pygame.draw.circle(screen, (90, 200, 255), m(g.ship.x, g.ship.y), 3)


def spawn_rock(t, mult, ship):  # чем дольше игра, тем чаще бронированные камни и кометы
    armored, comet = min(0.2, max(0, (t - 25) / 200)), min(0.25, max(0, (t - 15) / 150))
    r = random.random()
    rock = Rock(mult, kind="armored" if r < armored else "comet" if r < armored + comet else "normal")
    rock.x, rock.y = random.randint(int(cx) - MARGIN, int(cx) + W + MARGIN), cy - rock.size  # над окном
    if rock.kind == "comet":
        rock.aim_at(ship.x, ship.y)
    return rock


def pick_buff(lives):  # жизнь не выпадает, если жизней уже максимум
    kinds = list(BUFFS)
    return random.choices(kinds, [0 if k == "life" and lives >= MAX_LIVES else BUFFS[k]["weight"] for k in kinds])[0]


def new_game():
    return N(ship=Ship(WORLD_W // 2, WORLD_H - 120), rocks=[], bullets=[], pups=[], ufos=[], shots=[],
             t=0.0, score=0, lives=3, timer=0.0, next_ufo=20.0)


background = pygame.Surface((W, H))
for y in range(H):  # вертикальный градиент
    pygame.draw.line(background, [int(a + (b - a) * y / (H - 1)) for a, b in zip((5, 5, 30), (60, 40, 120))], (0, y), (W, y))
stars = [[random.randint(0, W), random.randint(0, H), random.randint(1, 3), random.uniform(0, 6.28)]
         for _ in range(150)]  # x, y, радиус, фаза

g, best, state, over_delay, dt = new_game(), 0.0, "play", 0.0, 1 / 60
running = True
while running:
    # 1. События
    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            running = False
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE and state == "over" and over_delay <= 0:
            g, state = new_game(), "play"
    ship = g.ship
    keys = pygame.key.get_pressed()
    if state == "play":
        ship.update(keys, dt)
    cx, cy = max(0, min(WORLD_W - W, ship.x - W / 2)), max(0, min(WORLD_H - H, ship.y - H / 2))  # камера

    # 2. Обновление
    for s in stars:
        s[1] += s[2] * 0.8
        if s[1] > H:
            s[0], s[1] = random.randint(0, W), 0

    rain = warning = False
    if state == "play":
        g.t += dt
        mult = 1 + g.t / 40
        interval = max(0.25, 0.9 - g.t * 0.01)
        if g.t >= 30:  # каждые 35 с: предупреждение (2 с), затем ливень (6 с)
            phase = (g.t - 30) % 35
            warning, rain = phase < 2, 2 <= phase < 8
        if rain:
            interval /= 2
        interval *= W / (W + 2 * MARGIN)  # камни появляются шире окна — сохраняем плотность
        scale = 0.4 if ship.has("slow") else 1.0  # баф «Баяу уақыт»

        if keys[pygame.K_SPACE] and ship.cooldown <= 0:
            g.bullets += ship.shoot()
        g.timer += dt
        while g.timer >= interval:
            g.timer -= interval
            g.rocks.append(spawn_rock(g.t, mult, ship))
        if g.t >= g.next_ufo:  # НЛО появляется сверху окна раз в 25–40 с
            g.ufos.append(UFO(cx + random.randint(200, W - 200), cy - 80))
            g.next_ufo = g.t + random.uniform(25, 40)

        for r in g.rocks:
            r.update(scale)
        for u in g.ufos:
            shot = u.update(ship, dt, scale)
            if shot:
                g.shots.append(shot)
        g.ufos = [u for u in g.ufos if u.age < UFO.LIFE]
        for s in g.shots:
            s.x, s.y = s.x + s.vx * scale, s.y + s.vy * scale
        g.shots = [s for s in g.shots if -100 <= s.x - cx <= W + 100 and -100 <= s.y - cy <= H + 100]
        for b in g.bullets:
            b.x, b.y = b.x + b.vx, b.y - BULLET_SPEED
        g.bullets = [b for b in g.bullets if b.y >= cy - 20 and cx - 20 <= b.x <= cx + W + 20]

        for b in g.bullets[:]:  # пули × камни и НЛО
            for t in g.rocks[:] + g.ufos:
                if dist(b, t) < t.hit + BULLET_R:
                    g.bullets.remove(b)
                    t.hp -= 1
                    if t.hp <= 0:
                        for lst in (g.rocks, g.ufos):
                            if t in lst:
                                lst.remove(t)
                        g.rocks += t.split(mult)
                        g.score += KINDS[t.kind]["points"]
                        if random.random() < KINDS[t.kind]["drop"]:
                            g.pups.append(N(kind=pick_buff(g.lives), x=t.x, y=t.y, age=0.0))
                    break  # пуля потрачена

        for p in g.pups[:]:  # бафы падают, корабль их подбирает
            p.y, p.age = p.y + 3, p.age + dt
            if dist(p, ship) < PICKUP_R + SHIP_R + 6:
                g.pups.remove(p)
                if p.kind == "life":
                    g.lives = min(MAX_LIVES, g.lives + 1)
                else:
                    ship.add_buff(p.kind)
            elif p.y > cy + H + 30:
                g.pups.remove(p)

        # камни, ушедшие вниз или далеко за край окна = +1 очко
        alive = [r for r in g.rocks if r.y <= cy + H + r.size and abs(r.x - cx - W / 2) <= W / 2 + 2 * MARGIN]
        g.score += len(g.rocks) - len(alive)
        g.rocks = alive

        if ship.invincible <= 0:  # корабль × камни, выстрелы и сам НЛО
            h = next((h for h in g.rocks + g.shots + g.ufos if dist(h, ship) < h.hit + SHIP_R), None)
            if h:
                for lst in (g.rocks, g.shots):  # камень и выстрел исчезают, НЛО остаётся
                    lst[:] = [x for x in lst if x is not h]
                if ship.shield:
                    ship.shield, ship.invincible = False, 1.0
                else:
                    g.lives, ship.invincible = g.lives - 1, 1.5

        if g.lives <= 0:
            state, over_delay, best = "over", 0.8, max(best, g.t)
    else:
        over_delay -= dt

    # 3. Рисование
    screen.blit(background, (0, 0))
    now = pygame.time.get_ticks() / 1000
    for x, y, r, ph in stars:  # звёзды с параллаксом: ближние (крупные) двигаются быстрее
        c = int(170 + 85 * math.sin(now * 2 + ph))
        pygame.draw.circle(screen, (c, c, c), (int((x - cx * r * 0.1) % W), int((y - cy * r * 0.1) % H)), r)
    pygame.draw.rect(screen, (255, 220, 60), (int(-cx), int(-cy), WORLD_W, WORLD_H), 4)  # граница карты
    for r in g.rocks:
        r.draw()
    for u in g.ufos:
        u.draw()
    for s in g.shots:
        pos = (int(s.x - cx), int(s.y - cy))
        pygame.draw.circle(screen, (255, 70, 200), pos, 10)
        pygame.draw.circle(screen, WHITE, pos, 4)
    for p in g.pups:
        info, pos = BUFFS[p.kind], (int(p.x - cx), int(p.y - cy))
        rad = int(PICKUP_R + 3 * math.sin(p.age * 6))  # «дышит»
        pygame.draw.circle(screen, (20, 20, 50), pos, rad + 4)
        pygame.draw.circle(screen, info["color"], pos, rad)
        pygame.draw.circle(screen, WHITE, pos, rad, 3)
        label = small_font.render(info["letter"], True, WHITE)
        screen.blit(label, label.get_rect(center=pos))
    for b in g.bullets:
        x, y, n = b.x - cx, b.y - cy, math.hypot(b.vx, BULLET_SPEED)  # хвост тянется назад вдоль полёта
        pygame.draw.line(screen, (255, 200, 60), (x, y), (x - b.vx / n * 18, y + BULLET_SPEED / n * 18), 6)
        pygame.draw.circle(screen, (255, 255, 220), (int(x), int(y)), BULLET_R)
    if state == "play":
        ship.draw()

    pygame.draw.rect(screen, (20, 20, 60), (20, 20, 340, 150), border_radius=12)
    pygame.draw.rect(screen, (255, 220, 60), (20, 20, 340, 150), 3, border_radius=12)
    text(font, f"Уақыт: {g.t:.1f} с", (40, 30))
    text(font, f"Ұпай: {g.score}", (40, 75))
    text(font, f"Өмір: {g.lives}", (40, 120), (255, 120, 120))
    minimap(g)

    if state == "play":
        active = [("shield", BUFFS["shield"]["name"])] if ship.shield else []
        active += [(k, f"{BUFFS[k]['name']}: {ship.buffs[k]:.0f} с") for k in ship.buffs if ship.has(k)]
        for i, (kind, label) in enumerate(active):  # список активных бафов под панелью
            pygame.draw.circle(screen, BUFFS[kind]["color"], (36, 204 + 36 * i), 9)
            text(small_font, label, (56, 190 + 36 * i), BUFFS[kind]["color"])
        text(font, "Ату: ПРОБЕЛ", (40, H - 60), (180, 220, 255))
        if warning and int(g.t * 4) % 2 == 0:
            center(big_font, "Назар аударыңыз!", 120, (255, 200, 60))
        elif rain:
            center(font, "Тас жаңбыры!", 40, (255, 120, 120))
    else:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        center(big_font, "Ойын аяқталды!", 230, (255, 120, 120))
        center(font, f"Шыдаған уақыт: {g.t:.1f} с", 380)
        center(font, f"Ұпай: {g.score}", 430)
        center(font, f"Рекорд: {best:.1f} с", 480, (255, 220, 60))
        center(font, "Қайта бастау: ПРОБЕЛ    Шығу: ESC", 580, (180, 220, 255))

    pygame.display.flip()
    dt = min(clock.tick(60) / 1000, 0.05)  # 4. Ожидание

pygame.quit()