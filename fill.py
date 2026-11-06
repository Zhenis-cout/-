import math
import random
import pygame

WIDTH, HEIGHT = 1920, 1080

FIRE_DELAY = 0.18  # пауза между выстрелами (секунды)
SPLIT_SIZE = 34    # камни крупнее раскалываются на два, мелкие просто исчезают
MAX_LIVES = 5      # больше жизней набрать нельзя

# ---------- БАФЫ ----------
# time = сколько секунд действует (0 = мгновенный или до первого удара)
# weight = насколько часто выпадает (больше = чаще)
BUFFS = {
    "triple": {"letter": "3", "color": (255, 160, 40), "name": "Үш ату", "time": 10, "weight": 3},
    "rapid": {"letter": "R", "color": (255, 90, 90), "name": "Жылдам ату", "time": 8, "weight": 3},
    "shield": {"letter": "S", "color": (80, 170, 255), "name": "Қалқан", "time": 0, "weight": 2},
    "slow": {"letter": "Z", "color": (170, 120, 255), "name": "Баяу уақыт", "time": 6, "weight": 2},
    "life": {"letter": "+", "color": (90, 230, 120), "name": "Өмір +1", "time": 0, "weight": 1},
}

# ---------- ВИДЫ КАМНЕЙ ----------
POINTS = {"normal": 1, "armored": 5, "comet": 3}          # очки за уничтожение
DROP_CHANCE = {"normal": 0.08, "armored": 0.6, "comet": 0.2}  # шанс выпадения бафа


def make_gradient(width, height, top_color, bottom_color):
    surface = pygame.Surface((width, height))
    for y in range(height):
        t = y / (height - 1)
        color = (
            int(top_color[0] + (bottom_color[0] - top_color[0]) * t),
            int(top_color[1] + (bottom_color[1] - top_color[1]) * t),
            int(top_color[2] + (bottom_color[2] - top_color[2]) * t),
        )
        pygame.draw.line(surface, color, (0, y), (width, y))
    return surface


class Ship:
    RADIUS = 16  # соқтығысу радиусы

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 9
        self.invincible = 0.0  # соққыдан кейінгі қорғаныс уақыты (секунд)
        self.cooldown = 0.0    # сколько секунд осталось до следующего выстрела
        self.shield = False    # НОВОЕ: щит поглощает один удар
        # НОВОЕ: оставшееся время действия временных бафов
        self.buffs = {"triple": 0.0, "rapid": 0.0, "slow": 0.0}

    def has(self, kind):
        return self.buffs.get(kind, 0.0) > 0

    def add_buff(self, kind):
        if kind == "shield":
            self.shield = True
        else:
            self.buffs[kind] = BUFFS[kind]["time"]  # повторный подбор обновляет таймер

    def update(self, keys, dt):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += self.speed
        # экраннан шығып кетпесін
        self.x = max(25, min(WIDTH - 25, self.x))
        self.y = max(40, min(HEIGHT - 40, self.y))
        if self.invincible > 0:
            self.invincible -= dt
        if self.cooldown > 0:
            self.cooldown -= dt
        for kind in self.buffs:
            self.buffs[kind] = max(0.0, self.buffs[kind] - dt)

    def shoot(self):
        """Возвращает список новых пуль. Зависит от активных бафов."""
        # «Жылдам ату» ускоряет стрельбу больше чем вдвое
        self.cooldown = FIRE_DELAY * (0.4 if self.has("rapid") else 1.0)
        if self.has("triple"):
            return [
                Bullet(self.x, self.y - 30),
                Bullet(self.x - 14, self.y - 20, -4),  # левая пуля летит чуть влево
                Bullet(self.x + 14, self.y - 20, 4),   # правая — чуть вправо
            ]
        return [Bullet(self.x, self.y - 30)]

    def draw(self, screen):
        x, y = self.x, self.y
        # НОВОЕ: кольцо щита (рисуем до мигания, чтобы щит не пропадал)
        if self.shield:
            pulse = 2 * math.sin(pygame.time.get_ticks() / 120)
            pygame.draw.circle(screen, BUFFS["shield"]["color"],
                               (int(x), int(y)), int(40 + pulse), 3)
        # соққыдан кейін кеме жыпылықтайды
        if self.invincible > 0 and int(self.invincible * 10) % 2 == 0:
            return
        # қозғалтқыш жалыны
        flame = [(x - 8, y + 14), (x + 8, y + 14), (x, y + 26 + random.randint(0, 14))]
        pygame.draw.polygon(screen, (255, 150, 40), flame)
        # кеме корпусы
        body = [(x, y - 30), (x + 22, y + 22), (x, y + 11), (x - 22, y + 22)]
        pygame.draw.polygon(screen, (90, 200, 255), body)
        pygame.draw.polygon(screen, (230, 250, 255), body, 3)
        pygame.draw.circle(screen, (20, 30, 80), (int(x), int(y - 6)), 5)  # кабина


class Bullet:
    RADIUS = 5
    # скорость выбрана с запасом, чтобы пуля не пролетала сквозь быстрые камни
    SPEED = 22

    def __init__(self, x, y, vx=0):
        self.x = x
        self.y = y
        self.vx = vx  # НОВОЕ: боковая скорость (для тройного выстрела)

    def update(self):
        self.x += self.vx
        self.y -= Bullet.SPEED

    def is_off(self):
        return self.y < -20 or self.x < -20 or self.x > WIDTH + 20

    def draw(self, screen):
        # хвост тянется назад вдоль направления полёта
        length = math.hypot(self.vx, Bullet.SPEED)
        tail = (self.x - self.vx / length * 18, self.y + Bullet.SPEED / length * 18)
        pygame.draw.line(screen, (255, 200, 60), (self.x, self.y), tail, 6)
        pygame.draw.circle(screen, (255, 255, 220), (int(self.x), int(self.y)), 5)


class PowerUp:
    """НОВОЕ: бонус, который падает вниз. Корабль подбирает его касанием."""
    RADIUS = 20

    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = x
        self.y = y
        self.speed = 3
        self.age = 0.0

    def update(self, dt):
        self.y += self.speed
        self.age += dt

    def is_off(self):
        return self.y > HEIGHT + 30

    def draw(self, screen, font):
        info = BUFFS[self.kind]
        pos = (int(self.x), int(self.y))
        r = int(self.RADIUS + 3 * math.sin(self.age * 6))  # «дышит»
        pygame.draw.circle(screen, (20, 20, 50), pos, r + 4)
        pygame.draw.circle(screen, info["color"], pos, r)
        pygame.draw.circle(screen, (255, 255, 255), pos, r, 3)
        label = font.render(info["letter"], True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=pos))


class Rock:
    def __init__(self, speed_mult, size=None, x=None, y=None, drift=None, kind="normal"):
        # kind: "normal" — обычный, "armored" — бронированный, "comet" — быстрая комета
        self.kind = kind
        if size is None:
            if kind == "armored":
                size = random.randint(50, 64)
            elif kind == "comet":
                size = random.randint(16, 24)
            else:
                size = random.randint(22, 50)
        self.size = size
        self.x = x if x is not None else random.randint(self.size, WIDTH - self.size)
        self.y = y if y is not None else -self.size
        self.speed = random.uniform(4, 7) * speed_mult
        if kind == "comet":
            self.speed *= 1.8   # кометы летят почти вдвое быстрее
        elif kind == "armored":
            self.speed *= 0.7   # бронированные тяжелее и медленнее
        # шетке қарай аздап ауытқу
        self.drift = drift if drift is not None else random.uniform(-1.5, 1.5)
        self.hp = 3 if kind == "armored" else 1  # сколько попаданий выдерживает
        self.angle = random.uniform(0, 360)
        self.spin = random.uniform(-3, 3)
        # тастың пішіні біркелкі емес болуы үшін әр төбенің радиусы әртүрлі
        self.shape = [random.uniform(0.7, 1.0) for _ in range(random.randint(8, 11))]

    def aim_at(self, tx, ty):
        """Направить камень туда, где сейчас находится корабль (для комет)."""
        frames = max(1.0, (ty - self.y) / self.speed)
        self.drift = max(-6.0, min(6.0, (tx - self.x) / frames))

    def update(self, scale=1.0):
        # scale < 1 замедляет камни (баф «Баяу уақыт»)
        self.y += self.speed * scale
        self.x += self.drift * scale
        self.angle += self.spin * scale

    def is_off(self):
        return self.y > HEIGHT + self.size

    def split(self, speed_mult):
        """Осколки, которые остаются после уничтожения камня."""
        if self.size < SPLIT_SIZE:
            return []  # мелкий камень просто исчезает
        new_size = int(self.size * 0.6)
        return [
            Rock(speed_mult, new_size, self.x - new_size, self.y, self.drift - 2),
            Rock(speed_mult, new_size, self.x + new_size, self.y, self.drift + 2),
        ]

    def draw(self, screen):
        # цвета зависят от вида камня
        if self.kind == "armored":
            fill = {3: (90, 105, 135), 2: (115, 100, 125), 1: (150, 90, 90)}[self.hp]
            edge, width = (170, 200, 240), 5  # чем меньше hp, тем краснее камень
        elif self.kind == "comet":
            fill, edge, width = (200, 80, 60), (255, 200, 120), 3
            # огненный хвост: треугольник назад от направления полёта
            length = math.hypot(self.drift, self.speed)
            dx, dy = self.drift / length, self.speed / length
            px, py = -dy * self.size * 0.7, dx * self.size * 0.7
            tail = (self.x - dx * self.size * 4, self.y - dy * self.size * 4)
            pygame.draw.polygon(screen, (255, 140, 50),
                                [(self.x + px, self.y + py), (self.x - px, self.y - py), tail])
        else:
            fill, edge, width = (125, 110, 100), (190, 175, 160), 3

        n = len(self.shape)
        coords = []
        for i, k in enumerate(self.shape):
            a = math.radians(self.angle) + 2 * math.pi / n * i
            coords.append((self.x + self.size * k * math.cos(a),
                           self.y + self.size * k * math.sin(a)))
        pygame.draw.polygon(screen, fill, coords)
        pygame.draw.polygon(screen, edge, coords, width)


def draw_text(screen, font, text, pos, color=(255, 255, 255)):
    screen.blit(font.render(text, True, (0, 0, 0)), (pos[0] + 2, pos[1] + 2))
    screen.blit(font.render(text, True, color), pos)


def draw_center(screen, font, text, y, color=(255, 255, 255)):
    w = font.size(text)[0]
    draw_text(screen, font, text, ((WIDTH - w) // 2, y), color)


def spawn_rock(elapsed, speed_mult, ship):
    """НОВОЕ: выбирает вид камня. Чем дольше игра, тем чаще редкие виды."""
    armored_chance = 0.0 if elapsed < 25 else min(0.2, (elapsed - 25) / 200)
    comet_chance = 0.0 if elapsed < 15 else min(0.25, (elapsed - 15) / 150)
    r = random.random()
    if r < armored_chance:
        return Rock(speed_mult, kind="armored")
    if r < armored_chance + comet_chance:
        rock = Rock(speed_mult, kind="comet")
        rock.aim_at(ship.x, ship.y)
        return rock
    return Rock(speed_mult)


def pick_buff(lives):
    """Случайный баф с учётом весов. Жизнь не выпадает, если жизней уже максимум."""
    kinds = list(BUFFS)
    weights = [BUFFS[k]["weight"] for k in kinds]
    if lives >= MAX_LIVES:
        weights[kinds.index("life")] = 0
    return random.choices(kinds, weights)[0]


def new_game():
    ship = Ship(WIDTH // 2, HEIGHT - 120)
    # кеме, тастар, пулалар, БАФЫ, уақыт, ұпай, өмір, таймер
    return ship, [], [], [], 0.0, 0, 3, 0.0


pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Тастардан жалтар!")
clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 36, bold=True)
small_font = pygame.font.SysFont("arial", 26, bold=True)
big_font = pygame.font.SysFont("arial", 90, bold=True)

background = make_gradient(WIDTH, HEIGHT, (5, 5, 30), (60, 40, 120))

# фондағы жұлдыздар: [x, y, радиус, фаза]
bg_dots = [
    [random.randint(0, WIDTH), random.randint(0, HEIGHT),
     random.randint(1, 3), random.uniform(0, 6.28)]
    for _ in range(150)
]

ship, rocks, bullets, powerups, elapsed, score, lives, spawn_timer = new_game()
best_time = 0.0
state = "play"  # "play" немесе "over"
over_delay = 0.0  # после смерти ПРОБЕЛ не перезапускает игру первые 0.8 с
dt = 1 / 60

running = True
while running:
    # 1. Оқиғалар
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE and state == "over" and over_delay <= 0:
                ship, rocks, bullets, powerups, elapsed, score, lives, spawn_timer = new_game()
                state = "play"

    # 2. Жаңарту
    for d in bg_dots:  # фон жұлдыздары төмен жылжиды
        d[1] += d[2] * 0.8
        if d[1] > HEIGHT:
            d[1] = 0
            d[0] = random.randint(0, WIDTH)

    rain = warning = False  # НОВОЕ: события «тас жаңбыры»

    if state == "play":
        elapsed += dt
        keys = pygame.key.get_pressed()
        ship.update(keys, dt)

        # уақыт өткен сайын қиындай түседі
        speed_mult = 1 + elapsed / 40
        spawn_interval = max(0.25, 0.9 - elapsed * 0.01)

        # НОВОЕ: каждые 35 с после 30-й секунды — предупреждение (2 с) и ливень камней (6 с)
        if elapsed >= 30:
            phase = (elapsed - 30) % 35
            warning = phase < 2
            rain = 2 <= phase < 8
        if rain:
            spawn_interval /= 2

        # стрельба (можно держать пробел)
        if keys[pygame.K_SPACE] and ship.cooldown <= 0:
            bullets.extend(ship.shoot())

        spawn_timer += dt
        while spawn_timer >= spawn_interval:
            spawn_timer -= spawn_interval
            rocks.append(spawn_rock(elapsed, speed_mult, ship))

        rock_scale = 0.4 if ship.has("slow") else 1.0
        for rock in rocks:
            rock.update(rock_scale)

        # двигаем пули и убираем улетевшие за экран
        for bullet in bullets[:]:
            bullet.update()
            if bullet.is_off():
                bullets.remove(bullet)

        # попадания пуль в камни
        for bullet in bullets[:]:
            for rock in rocks[:]:
                dist = math.hypot(rock.x - bullet.x, rock.y - bullet.y)
                if dist < rock.size * 0.85 + Bullet.RADIUS:
                    bullets.remove(bullet)
                    rock.hp -= 1
                    if rock.hp <= 0:  # камень уничтожен
                        rocks.remove(rock)
                        rocks.extend(rock.split(speed_mult))
                        score += POINTS[rock.kind]
                        if random.random() < DROP_CHANCE[rock.kind]:
                            powerups.append(PowerUp(pick_buff(lives), rock.x, rock.y))
                    break  # эта пуля уже потрачена

        # НОВОЕ: бафы падают вниз, корабль их подбирает
        for p in powerups[:]:
            p.update(dt)
            if math.hypot(p.x - ship.x, p.y - ship.y) < PowerUp.RADIUS + Ship.RADIUS + 6:
                powerups.remove(p)
                if p.kind == "life":
                    lives = min(MAX_LIVES, lives + 1)
                else:
                    ship.add_buff(p.kind)
            elif p.is_off():
                powerups.remove(p)

        # жерге түскен тастар = өтіп кетті = +1 ұпай
        for rock in rocks[:]:
            if rock.is_off():
                rocks.remove(rock)
                score += 1

        # соқтығысу
        if ship.invincible <= 0:
            for rock in rocks:
                dist = math.hypot(rock.x - ship.x, rock.y - ship.y)
                if dist < rock.size * 0.85 + Ship.RADIUS:
                    rocks.remove(rock)
                    if ship.shield:  # щит принимает удар на себя
                        ship.shield = False
                        ship.invincible = 1.0
                    else:
                        lives -= 1
                        ship.invincible = 1.5
                    break

        if lives <= 0:
            state = "over"
            over_delay = 0.8
            best_time = max(best_time, elapsed)
    else:
        over_delay -= dt

    # 3. Салу
    screen.blit(background, (0, 0))

    t = pygame.time.get_ticks() / 1000
    for x, y, r, phase_ in bg_dots:
        b = int(170 + 85 * math.sin(t * 2 + phase_))
        pygame.draw.circle(screen, (b, b, b), (int(x), int(y)), r)

    for rock in rocks:
        rock.draw(screen)

    for p in powerups:
        p.draw(screen, small_font)

    for bullet in bullets:
        bullet.draw(screen)

    if state == "play":
        ship.draw(screen)

    # ақпарат тақтасы
    pygame.draw.rect(screen, (20, 20, 60), (20, 20, 340, 150), border_radius=12)
    pygame.draw.rect(screen, (255, 220, 60), (20, 20, 340, 150), 3, border_radius=12)
    draw_text(screen, font, f"Уақыт: {elapsed:.1f} с", (40, 30))
    draw_text(screen, font, f"Ұпай: {score}", (40, 75))
    draw_text(screen, font, f"Өмір: {lives}", (40, 120), (255, 120, 120))

    # НОВОЕ: список активных бафов под панелью
    if state == "play":
        y = 190
        active = []
        if ship.shield:
            active.append(("shield", BUFFS["shield"]["name"]))
        for kind in ("triple", "rapid", "slow"):
            if ship.has(kind):
                active.append((kind, f"{BUFFS[kind]['name']}: {ship.buffs[kind]:.0f} с"))
        for kind, label in active:
            color = BUFFS[kind]["color"]
            pygame.draw.circle(screen, color, (36, y + 14), 9)
            draw_text(screen, small_font, label, (56, y), color)
            y += 36

        draw_text(screen, font, "Ату: ПРОБЕЛ", (40, HEIGHT - 60), (180, 220, 255))

        # НОВОЕ: баннеры событий
        if warning and int(elapsed * 4) % 2 == 0:
            draw_center(screen, big_font, "Назар аударыңыз!", 120, (255, 200, 60))
        elif rain:
            draw_center(screen, font, "Тас жаңбыры!", 40, (255, 120, 120))

    if state == "over":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        draw_center(screen, big_font, "Ойын аяқталды!", 230, (255, 120, 120))
        draw_center(screen, font, f"Шыдаған уақыт: {elapsed:.1f} с", 380)
        draw_center(screen, font, f"Ұпай: {score}", 430)
        draw_center(screen, font, f"Рекорд: {best_time:.1f} с", 480, (255, 220, 60))
        draw_center(screen, font, "Қайта бастау: ПРОБЕЛ    Шығу: ESC", 580, (180, 220, 255))

    pygame.display.flip()

    # 4. Күту
    dt = min(clock.tick(60) / 1000, 0.05)

pygame.quit()