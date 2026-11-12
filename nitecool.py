import math
import random

import pygame


# ==================== settings.py ====================
W, H = 1920, 1080              # терезе өлшемі
WORLD_W, WORLD_H = 3840, 2160  # карта өлшемі (терезеден екі есе үлкен)
FPS = 60
LEVEL_PAUSE = 2.5              # деңгей аяқталған соңғы үзіліс (секунд)

# Деңгейлер. time — өту үшін аман қалу секундтары, speed — тас жылдамдығының еселеуіші,
# interval — тастардың шығу аралығы, armored/comet — сауытты тас пен комета ықтималдығы,
# ufo — НЛО келу аралығы (мин, макс) немесе None, rain — тас жаңбыры бар ма
LEVELS = [
    dict(name="Бастау", time=25, speed=0.8, interval=1.0, armored=0.0, comet=0.0, ufo=None, rain=False),
    dict(name="Жылдамдау", time=45, speed=1.0, interval=0.9, armored=0.1, comet=0.1, ufo=None, rain=False),
    dict(name="Кометалар", time=50, speed=1.2, interval=0.8, armored=0.15, comet=0.2, ufo=(25, 35), rain=False),
    dict(name="Қауіп", time=67, speed=1.4, interval=0.7, armored=0.2, comet=0.25, ufo=(20, 30), rain=True),
    dict(name="Соңғы шайқас", time=80, speed=1.6, interval=0.6, armored=0.25, comet=0.3, ufo=(15, 25), rain=True),
]

FIRE_DELAY, SPLIT_SIZE, MAX_LIVES = 0.18, 34, 5
BULLET_SPEED, BULLET_R, SHIP_R, PICKUP_R = 22, 5, 16, 20
SHOT_SPEED, MARGIN = 9, 300    # НЛО оғының жылдамдығы; тастар терезеден MARGIN px тыс шығады

WHITE = (255, 255, 255)

# time — әсер ету уақыты (0 = бірінші соққыға дейін), weight — түсу жиілігі
BUFFS = {
    "triple": {"letter": "3", "color": (255, 160, 40), "name": "Үш ату", "time": 10, "weight": 3},
    "rapid": {"letter": "R", "color": (255, 90, 90), "name": "Жылдам ату", "time": 8, "weight": 3},
    "shield": {"letter": "S", "color": (80, 170, 255), "name": "Қалқан", "time": 0, "weight": 2},
    "slow": {"letter": "Z", "color": (170, 120, 255), "name": "Баяу уақыт", "time": 6, "weight": 2},
    "life": {"letter": "+", "color": (90, 230, 120), "name": "Өмір +1", "time": 0, "weight": 1},
}

# size — өлшем аралығы, speed — жылдамдық еселеуіші, hp — бұзылғанға дейінгі соққы,
# points — ұпай, drop — бонус түсу ықтималдығы
KINDS = {
    "normal": dict(size=(22, 50), speed=1.0, hp=1, points=1, drop=0.08),
    "armored": dict(size=(50, 64), speed=0.7, hp=3, points=5, drop=0.6),
    "comet": dict(size=(16, 24), speed=1.8, hp=1, points=3, drop=0.2),
    "ufo": dict(hp=10, points=15, drop=1.0),  # НЛО әрқашан бонус тастайды
}


# ==================== game_object.py ====================
class GameObject:
    """Ойындағы барлық нысандардың ата-ана класы.

    Балалар класс update(), draw(), hit(), on_destroy() әдістерін қайта анықтайды (override).
    """

    points = 0         # жойылғанда берілетін ұпай
    drop_chance = 0.0  # жойылғанда бонус түсу ықтималдығы

    def __init__(self, x, y, radius, hp=1):
        self.x, self.y = x, y
        self.radius = radius  # соқтығысу радиусы
        self.hp = hp
        self.alive = True

    def update(self, game, dt):
        """Әр кадрда шақырылады. Әр класс өзінше жүзеге асырады."""

    def draw(self, screen, cam):
        """cam = (cx, cy) — камераның сол жақ жоғарғы бұрышы. Әр класс өзінше салады."""

    def screen_pos(self, cam):
        return self.x - cam[0], self.y - cam[1]

    def collides_with(self, other):
        return math.hypot(self.x - other.x, self.y - other.y) < self.radius + other.radius

    def hit(self, damage=1):
        """Соққы алу. Нысан жойылса True қайтарады."""
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def on_destroy(self, game):
        """Нысан жойылғанда шақырылады (мысалы, тас бөлшектерге ыдырайды)."""

    def on_ship_collision(self):
        """Кеме осы нысанға соқтығысқанда не болатыны. Әдепкі: нысан жоғалады."""
        self.alive = False


# ==================== bullet.py ====================
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


# ==================== pickup.py ====================
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


# ==================== ship.py ====================
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


# ==================== rock.py ====================
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


# ==================== ufo.py ====================
class UFO(GameObject):
    """Кеменің үстінде қалқып, оған оқ атады және 20 секундтан кейін ұшып кетеді."""

    LIFE = 20

    def __init__(self, x, y):
        info = KINDS["ufo"]
        super().__init__(x, y, 42, hp=info["hp"])
        self.max_hp = info["hp"]
        self.points, self.drop_chance = info["points"], info["drop"]
        self.age, self.fire = 0.0, 1.5  # жасы; атуға дейінгі секунд

    def update(self, game, dt):  # override
        ship, scale = game.ship, game.time_scale
        self.age += dt * scale
        self.fire -= dt * scale
        if self.age >= self.LIFE:
            self.alive = False
            return
        leaving = self.age > self.LIFE - 3  # соңғы 3 с — жоғары ұшады, атпайды
        tx = max(60, min(WORLD_W - 60, ship.x + 350 * math.sin(self.age)))
        ty = -300 if leaving else (ship.y - 320 if ship.y >= 400 else ship.y + 320)
        self.x += max(-7, min(7, (tx - self.x) * 0.04)) * scale
        self.y += (ty - self.y) * 0.03 * scale
        if self.fire <= 0 and not leaving:
            self.fire = 1.4
            d = math.hypot(ship.x - self.x, ship.y - self.y) or 1
            game.shots.append(EnemyShot(self.x, self.y + 20,
                                        (ship.x - self.x) / d * SHOT_SPEED,
                                        (ship.y - self.y) / d * SHOT_SPEED))

    def on_ship_collision(self):  # override: НЛО кемеге тиіп жоғалмайды
        pass

    def draw(self, screen, cam):  # override
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        pygame.draw.ellipse(screen, (110, 230, 190), (x - 20, y - 28, 40, 34))  # күмбез
        pygame.draw.ellipse(screen, (150, 160, 185), (x - 44, y - 8, 88, 28))   # корпус
        pygame.draw.ellipse(screen, (220, 235, 255), (x - 44, y - 8, 88, 28), 3)
        blink = pygame.time.get_ticks() // 250
        for i, dx in enumerate((-28, 0, 28)):
            color = (255, 230, 90) if (blink + i) % 2 else (255, 120, 60)
            pygame.draw.circle(screen, color, (x + dx, y + 8), 4)
        pygame.draw.rect(screen, (90, 20, 20), (x - 30, y - 46, 60, 6))  # өмір жолағы
        pygame.draw.rect(screen, (255, 90, 90), (x - 30, y - 46, int(60 * max(self.hp, 0) / self.max_hp), 6))


# ==================== game.py ====================
def pick_buff(lives):
    """Өмір максимумда болса, «өмір» бонусы түспейді."""
    kinds = list(BUFFS)
    weights = [0 if k == "life" and lives >= MAX_LIVES else BUFFS[k]["weight"] for k in kinds]
    return random.choices(kinds, weights)[0]


class Game:
    """Ойынның басты класы: күй, цикл, деңгейлер, соқтығысулар, жеңу/жеңілу/қайта бастау."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Тастардан жалтар!")
        self.clock = pygame.time.Clock()
        self.font, self.small_font, self.big_font = (
            pygame.font.SysFont("arial", s, bold=True) for s in (36, 26, 90))
        self.background = self._make_background()
        self.stars = [[random.randint(0, W), random.randint(0, H), random.randint(1, 3), random.uniform(0, 6.28)]
                      for _ in range(150)]  # x, y, радиус, фаза
        self.best = 0.0
        self.running = True
        self.reset()

    # ------------------------------------------------------------ күй
    def reset(self):
        """Жаңа ойын бастау (қайта бастау осы әдісті шақырады)."""
        self.ship = Ship(WORLD_W // 2, WORLD_H - 120)
        self.rocks, self.ufos, self.bullets, self.shots, self.pickups = [], [], [], [], []
        self.t = 0.0       # бүкіл ойын уақыты
        self.score = 0
        self.time_scale = 1.0
        self.rain = self.warning = False
        self.state = "play"  # "play" | "level" (деңгей өтті) | "won" | "lost"
        self.over_delay = 0.0
        self.keys = pygame.key.get_pressed()
        self.cam_x = self.cam_y = 0.0
        self.update_camera()
        self.start_level(0)

    @property
    def cfg(self):
        """Ағымдағы деңгейдің баптаулары."""
        return LEVELS[self.level]

    def start_level(self, n):
        self.level = n
        self.lt = 0.0  # деңгей уақыты
        self.spawn_timer = 0.0
        self.next_ufo = random.uniform(*self.cfg["ufo"]) / 2 if self.cfg["ufo"] else None
        self.banner = 2.0  # «Деңгей N» жазуының көрсетілу уақыты
        self.state = "play"
        self.ship.invincible = max(self.ship.invincible, 1.0)

    @property
    def all_objects(self):
        """Барлық нысан бір тізімде (сурет салу ретімен). Полиморфизм осы тізім арқылы."""
        return (self.rocks + self.ufos + self.shots + self.pickups + self.bullets + [self.ship])

    def update_camera(self):
        self.cam_x = max(0, min(WORLD_W - W, self.ship.x - W / 2))
        self.cam_y = max(0, min(WORLD_H - H, self.ship.y - H / 2))

    # ------------------------------------------------------------ негізгі цикл
    def run(self):
        dt = 1 / FPS
        while self.running:
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
        pygame.quit()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_r):
                if self.state in ("won", "lost") and self.over_delay <= 0:
                    self.restart()

    # ------------------------------------------------------------ жаңарту
    def update(self, dt):
        self.keys = pygame.key.get_pressed()
        self.update_stars()
        if self.state in ("won", "lost"):
            self.over_delay -= dt
            return
        if self.state == "level":  # деңгейлер арасындағы үзіліс
            self.over_delay -= dt
            if self.over_delay <= 0:
                self.start_level(self.level + 1)
            return

        self.t += dt
        self.lt += dt
        self.banner = max(0.0, self.banner - dt)
        self.time_scale = 0.4 if self.ship.has("slow") else 1.0
        self.update_camera()
        self.spawn(dt)

        # Полиморфизм: бір тізім, бір цикл — әр нысан өз update() әдісін орындайды
        for obj in self.all_objects:
            if obj.alive:
                obj.update(self, dt)

        self.handle_collisions()
        self.remove_dead()
        self.update_camera()
        self.check_end()

    def update_stars(self):
        for s in self.stars:
            s[1] += s[2] * 0.8
            if s[1] > H:
                s[0], s[1] = random.randint(0, W), 0

    def spawn(self, dt):
        cfg, lt = self.cfg, self.lt
        mult = cfg["speed"] * (1 + lt / 60)  # деңгей ішінде де біртіндеп қиындайды
        interval = max(0.25, cfg["interval"] - lt * 0.005)
        self.rain = self.warning = False
        if cfg["rain"] and lt >= 12:  # әр 25 с сайын: ескерту (2 с), содан соң тас жаңбыры (6 с)
            phase = (lt - 12) % 25
            self.warning, self.rain = phase < 2, 2 <= phase < 8
        if self.rain:
            interval /= 2
        interval *= W / (W + 2 * MARGIN)  # тастар терезеден кеңірек шығады — тығыздықты сақтаймыз

        self.spawn_timer += dt
        while self.spawn_timer >= interval:
            self.spawn_timer -= interval
            self.rocks.append(self.make_rock(mult))
        if self.next_ufo is not None and lt >= self.next_ufo:  # НЛО терезенің жоғарысынан келеді
            self.ufos.append(UFO(self.cam_x + random.randint(200, W - 200), self.cam_y - 80))
            self.next_ufo = lt + random.uniform(*cfg["ufo"])

    def make_rock(self, mult):
        """Деңгейге қарай сауытты тастар мен кометалар жиірек шығады."""
        armored, comet = self.cfg["armored"], self.cfg["comet"]
        r = random.random()
        kind = "armored" if r < armored else "comet" if r < armored + comet else "normal"
        rock = Rock(mult, kind)
        rock.x = random.randint(int(self.cam_x) - MARGIN, int(self.cam_x) + W + MARGIN)
        rock.y = self.cam_y - rock.size
        if kind == "comet":
            rock.aim_at(self.ship.x, self.ship.y)
        return rock

    # ------------------------------------------------------------ соқтығысулар
    def handle_collisions(self):
        ship = self.ship

        # оқ × тас және НЛО
        for b in self.bullets:
            for target in self.rocks + self.ufos:
                if b.alive and target.alive and b.collides_with(target):
                    b.alive = False
                    if target.hit():  # hit() — полиморфты: жойылса True
                        self.on_destroyed(target)
                    break

        # кеме × бонус
        for p in self.pickups:
            if p.alive and ship.collides_with(p):
                p.apply(ship)

        # кеме × тас, НЛО оғы, НЛО
        if ship.invincible <= 0:
            for h in self.rocks + self.shots + self.ufos:
                if h.alive and ship.collides_with(h):
                    h.on_ship_collision()  # тас пен оқ жоғалады, НЛО қалады
                    ship.hit()
                    break

    def on_destroyed(self, obj):
        self.score += obj.points
        obj.on_destroy(self)  # тас бөлшектенеді, НЛО ештеңе істемейді
        if random.random() < obj.drop_chance:
            self.pickups.append(Pickup(pick_buff(self.ship.hp), obj.x, obj.y))

    def remove_dead(self):
        self.rocks = [o for o in self.rocks if o.alive]
        self.ufos = [o for o in self.ufos if o.alive]
        self.shots = [o for o in self.shots if o.alive]
        self.bullets = [o for o in self.bullets if o.alive]
        self.pickups = [o for o in self.pickups if o.alive]

    # ------------------------------------------------------------ деңгей / жеңу / жеңілу
    def check_level_complete(self):
        """Деңгей өтті: осы деңгейдің уақыты бойы аман қалды."""
        return self.ship.alive and self.lt >= self.cfg["time"]

    def check_win(self):
        """Жеңу: соңғы деңгей өтті."""
        return self.check_level_complete() and self.level == len(LEVELS) - 1

    def check_lose(self):
        """Жеңілу: барлық өмір таусылды."""
        return not self.ship.alive

    def check_end(self):
        if self.check_lose():
            self.finish("lost")
        elif self.check_win():
            self.finish("won")
        elif self.check_level_complete():
            self.finish_level()

    def finish_level(self):
        """Келесі деңгейге өту: қауіптерді тазалап, сыйға +1 өмір береміз."""
        self.rocks, self.ufos, self.bullets, self.shots = [], [], [], []
        self.ship.hp = min(MAX_LIVES, self.ship.hp + 1)
        self.state, self.over_delay = "level", LEVEL_PAUSE
        self.rain = self.warning = False

    def finish(self, state):
        self.state = state
        self.over_delay = 0.8  # кездейсоқ басып қайта бастап жібермеу үшін
        self.best = max(self.best, self.t)

    def restart(self):
        """Қайта бастау: жаңа ойын."""
        self.reset()

    # ------------------------------------------------------------ сурет салу
    def draw(self):
        cam = (self.cam_x, self.cam_y)
        self.screen.blit(self.background, (0, 0))
        now = pygame.time.get_ticks() / 1000
        for x, y, r, ph in self.stars:  # параллакс: үлкен жұлдыздар жылдамырақ қозғалады
            c = int(170 + 85 * math.sin(now * 2 + ph))
            pos = (int((x - cam[0] * r * 0.1) % W), int((y - cam[1] * r * 0.1) % H))
            pygame.draw.circle(self.screen, (c, c, c), pos, r)
        pygame.draw.rect(self.screen, (255, 220, 60), (int(-cam[0]), int(-cam[1]), WORLD_W, WORLD_H), 4)

        # Полиморфизм: бір тізім, бір цикл — әр нысан өзін өзі салады
        for obj in self.all_objects:
            if obj.alive:
                obj.draw(self.screen, cam)

        self.draw_hud()
        if self.state == "level":
            self.draw_level_screen()
        elif self.state in ("won", "lost"):
            self.draw_end_screen()

    def draw_hud(self):
        pygame.draw.rect(self.screen, (20, 20, 60), (20, 20, 420, 150), border_radius=12)
        pygame.draw.rect(self.screen, (255, 220, 60), (20, 20, 420, 150), 3, border_radius=12)
        self.text(self.font, f"Деңгей: {self.level + 1}/{len(LEVELS)}  {self.cfg['name']}", (40, 30))
        self.text(self.font, f"Ұпай: {self.score}", (40, 75))
        self.text(self.font, f"Өмір: {max(self.ship.hp, 0)}", (40, 120), (255, 120, 120))
        self.draw_minimap()
        if self.state != "play":
            return

        ship = self.ship
        active = [("shield", BUFFS["shield"]["name"])] if ship.shield else []
        active += [(k, f"{BUFFS[k]['name']}: {ship.buffs[k]:.0f} с") for k in ship.buffs if ship.has(k)]
        for i, (kind, label) in enumerate(active):
            pygame.draw.circle(self.screen, BUFFS[kind]["color"], (36, 204 + 36 * i), 9)
            self.text(self.small_font, label, (56, 190 + 36 * i), BUFFS[kind]["color"])
        self.text(self.font, "Ату: ПРОБЕЛ", (40, H - 60), (180, 220, 255))

        # деңгей аяқталуына дейінгі прогресс-жолақ
        total = self.cfg["time"]
        bw, bx, by = 600, (W - 600) // 2, H - 70
        pygame.draw.rect(self.screen, (20, 20, 60), (bx, by, bw, 26), border_radius=8)
        pygame.draw.rect(self.screen, (120, 255, 150), (bx, by, int(bw * min(1, self.lt / total)), 26),
                         border_radius=8)
        pygame.draw.rect(self.screen, (255, 220, 60), (bx, by, bw, 26), 3, border_radius=8)
        self.center(self.small_font, f"Деңгей аяқталуына: {max(0, total - self.lt):.0f} с", by - 34, (180, 255, 200))

        if self.banner > 0:
            self.center(self.big_font, f"Деңгей {self.level + 1}: {self.cfg['name']}", 300, (255, 220, 60))
        elif self.warning and int(self.lt * 4) % 2 == 0:
            self.center(self.big_font, "Назар аударыңыз!", 120, (255, 200, 60))
        elif self.rain:
            self.center(self.font, "Тас жаңбыры!", 40, (255, 120, 120))

    def draw_minimap(self):
        ox, oy, k = W - 260, H - 155, 240 / WORLD_W
        m = lambda x, y: (int(ox + x * k), int(oy + y * k))
        pygame.draw.rect(self.screen, (20, 20, 60), (ox, oy, 240, 135))
        pygame.draw.rect(self.screen, (255, 220, 60), (ox, oy, 240, 135), 2)
        pygame.draw.rect(self.screen, (150, 150, 200), (*m(self.cam_x, self.cam_y), int(W * k), int(H * k)), 1)
        for p in self.pickups:
            pygame.draw.circle(self.screen, BUFFS[p.kind]["color"], m(p.x, p.y), 3)
        for u in self.ufos:
            pygame.draw.circle(self.screen, (255, 80, 80), m(u.x, u.y), 4)
        pygame.draw.circle(self.screen, (90, 200, 255), m(self.ship.x, self.ship.y), 3)

    def draw_level_screen(self):
        self.center(self.big_font, f"Деңгей {self.level + 1} өтті!", 300, (120, 255, 150))
        self.center(self.font, "Сыйлық: Өмір +1", 430, (255, 120, 120))
        self.center(self.font, "Келесі деңгейге дайындал...", 480, (180, 220, 255))

    def draw_end_screen(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        if self.state == "won":
            self.center(self.big_font, "Жеңдіңіз!", 230, (120, 255, 150))
            self.center(self.font, f"Барлық {len(LEVELS)} деңгей өтті!", 380)
        else:
            self.center(self.big_font, "Ойын аяқталды!", 230, (255, 120, 120))
            self.center(self.font, f"Жеткен деңгей: {self.level + 1}/{len(LEVELS)}", 380)
        self.center(self.font, f"Уақыт: {self.t:.1f} с   Ұпай: {self.score}", 430)
        self.center(self.font, f"Рекорд: {self.best:.1f} с", 480, (255, 220, 60))
        self.center(self.font, "Қайта бастау: ПРОБЕЛ    Шығу: ESC", 580, (180, 220, 255))

    # ------------------------------------------------------------ көмекші
    def text(self, font, s, pos, color=WHITE):
        self.screen.blit(font.render(s, True, (0, 0, 0)), (pos[0] + 2, pos[1] + 2))
        self.screen.blit(font.render(s, True, color), pos)

    def center(self, font, s, y, color=WHITE):
        self.text(font, s, ((W - font.size(s)[0]) // 2, y), color)

    @staticmethod
    def _make_background():
        surf = pygame.Surface((W, H))
        for y in range(H):  # тік градиент
            color = [int(a + (b - a) * y / (H - 1)) for a, b in zip((5, 5, 30), (60, 40, 120))]
            pygame.draw.line(surf, color, (0, y), (W, y))
        return surf


# ==================== main.py ====================
def main():
    Game().run()


if __name__ == "__main__":
    main()