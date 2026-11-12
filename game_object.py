import math


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
