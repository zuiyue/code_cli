#!/usr/bin/env python3
"""贪吃蛇游戏 - 优化版"""

import pygame
import random
import sys
from collections import deque
from pathlib import Path

# ── 初始化 ──────────────────────────────────────────────
pygame.init()

# ── 颜色 ────────────────────────────────────────────────
class Color:
    BG        = (15,  15,  20)
    GRID_LINE = (30,  30,  40)
    SNAKE_HEAD= (50,  220, 80)
    SNAKE_BODY= (40,  180, 70)
    SNAKE_OUTLINE=(30, 140, 55)
    FOOD      = (255, 70,  70)
    FOOD_GLOW = (255, 120, 120)
    PANEL_BG  = (22,  22,  30)
    TEXT      = (220, 220, 220)
    TEXT_DIM  = (120, 120, 130)
    SCORE     = (255, 215, 0)
    OVERLAY   = (0,   0,   0)

# ── 配置 ────────────────────────────────────────────────
BLOCK_SIZE  = 22
GRID_W      = 28
GRID_H      = 20
PANEL_W     = 220
WIN_W       = GRID_W * BLOCK_SIZE + PANEL_W
WIN_H       = GRID_H * BLOCK_SIZE
FPS         = 12
INIT_SPEED  = 10
SPEED_STEP  = 2
SPEED_INTERVAL = 50  # 每吃多少食物加速一次

# ── 方向 ────────────────────────────────────────────────
DIR = {
    "UP":    (0, -1),
    "DOWN":  (0,  1),
    "LEFT":  (-1, 0),
    "RIGHT": (1,  0),
}
OPPOSITE = {DIR["UP"]: DIR["DOWN"], DIR["DOWN"]: DIR["UP"],
            DIR["LEFT"]: DIR["RIGHT"], DIR["RIGHT"]: DIR["LEFT"]}

# ── 字体 ────────────────────────────────────────────────
def _try_font(*names, size):
    for n in names:
        try:
            return pygame.font.SysFont(n, size)
        except Exception:
            continue
    return pygame.font.Font(None, size)

FONT_LARGE  = _try_font("simhei", "microsoftyahei", "notosanscjk", size=48)
FONT_MEDIUM = _try_font("simhei", "microsoftyahei", "notosanscjk", size=26)
FONT_SMALL  = _try_font("simhei", "microsoftyahei", "notosanscjk", size=18)


# ════════════════════════════════════════════════════════
#  蛇
# ════════════════════════════════════════════════════════
class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy = GRID_W // 2, GRID_H // 2
        self.body = deque([(cx, cy)])
        self.dir = DIR["RIGHT"]
        self.next_dir = DIR["RIGHT"]
        self._grow = False

    def steer(self, d):
        if d != OPPOSITE.get(self.dir):
            self.next_dir = d

    def move(self):
        self.dir = self.next_dir
        hx, hy = self.body[0]
        head = (hx + self.dir[0], hy + self.dir[1])
        self.body.appendleft(head)
        if not self._grow:
            self.body.pop()
        else:
            self._grow = False

    def grow(self):
        self._grow = True

    def collides(self):
        h = self.body[0]
        return (h[0] < 0 or h[0] >= GRID_W or h[1] < 0 or h[1] >= GRID_H
                or h in list(self.body)[1:])

    def draw(self, surf):
        for i, (x, y) in enumerate(self.body):
            px, py = x * BLOCK_SIZE, y * BLOCK_SIZE
            rect = pygame.Rect(px + 1, py + 1, BLOCK_SIZE - 2, BLOCK_SIZE - 2)
            if i == 0:
                pygame.draw.rect(surf, Color.SNAKE_HEAD, rect, border_radius=5)
                # 眼睛
                cx, cy = px + BLOCK_SIZE // 2, py + BLOCK_SIZE // 2
                dx, dy = self.dir
                off = 5
                for ex in (-3, 3):
                    ex2 = cx + ex + dx * off
                    ey2 = cy - 3 + dy * off
                    pygame.draw.circle(surf, (255, 255, 255), (ex2, ey2), 4)
                    pygame.draw.circle(surf, (0, 0, 0), (ex2, ey2), 2)
            else:
                t = i / max(len(self.body) - 1, 1)
                r = int(40 + (50 - 40) * t)
                g = int(180 - (180 - 140) * t)
                b = int(70 - (70 - 55) * t)
                color = (r, g, b)
                pygame.draw.rect(surf, color, rect, border_radius=4)
                pygame.draw.rect(surf, Color.SNAKE_OUTLINE, rect, 1, border_radius=4)


# ════════════════════════════════════════════════════════
#  食物
# ════════════════════════════════════════════════════════
class Food:
    def __init__(self, occupied):
        self.pos = self._spawn(occupied)
        self._anim = 0

    @staticmethod
    def _spawn(occupied):
        free = [(x, y) for x in range(GRID_W) for y in range(GRID_H)
                if (x, y) not in occupied]
        return random.choice(free) if free else (0, 0)

    def draw(self, surf):
        x, y = self.pos
        cx = x * BLOCK_SIZE + BLOCK_SIZE // 2
        cy = y * BLOCK_SIZE + BLOCK_SIZE // 2
        r = BLOCK_SIZE // 2 - 2
        # 光晕
        glow = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
        glow_radius = r + 4 + int(2 * __import__("math").sin(self._anim * 0.1))
        pygame.draw.circle(glow, (*Color.FOOD_GLOW, 60), (BLOCK_SIZE // 2, BLOCK_SIZE // 2), glow_radius)
        surf.blit(glow, (x * BLOCK_SIZE, y * BLOCK_SIZE))
        # 食物本体
        pygame.draw.circle(surf, Color.FOOD, (cx, cy), r)
        # 高光
        pygame.draw.circle(surf, (255, 180, 180), (cx - 3, cy - 3), r // 3)
        self._anim += 1


# ════════════════════════════════════════════════════════
#  粒子效果
# ════════════════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = float(x), float(y)
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-4, 1)
        self.life = 30
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            alpha = min(255, self.life * 8)
            s = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (3, 3), 3)
            surf.blit(s, (int(self.x), int(self.y)))


# ════════════════════════════════════════════════════════
#  游戏主类
# ════════════════════════════════════════════════════════
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("🐍 贪吃蛇")
        self.clock = pygame.time.Clock()
        self.font_large = FONT_LARGE
        self.font_med   = FONT_MEDIUM
        self.font_small = FONT_SMALL

        self.high_score = self._load_high()
        self.reset()

    # ── 持久化 ──
    @staticmethod
    def _high_path():
        return Path(__file__).parent / ".snake_highscore"

    def _load_high(self):
        try:
            return int(self._high_path().read_text().strip())
        except Exception:
            return 0

    def _save_high(self):
        self._high_path().write_text(str(self.high_score))

    # ── 重置 ──
    def reset(self):
        self.snake = Snake()
        self.food = Food(self.snake.body)
        self.score = 0
        self.eaten = 0
        self.speed = INIT_SPEED
        self.game_over = False
        self.paused = False
        self.particles = []

    # ── 事件 ──
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if self.game_over:
                    if e.key == pygame.K_r:
                        self.reset()
                    elif e.key == pygame.K_q:
                        return False
                else:
                    if e.key == pygame.K_p:
                        self.paused = not self.paused
                    elif not self.paused:
                        self._handle_dir(e.key)
        return True

    def _handle_dir(self, key):
        m = {
            pygame.K_UP: DIR["UP"],    pygame.K_w: DIR["UP"],
            pygame.K_DOWN: DIR["DOWN"], pygame.K_s: DIR["DOWN"],
            pygame.K_LEFT: DIR["LEFT"], pygame.K_a: DIR["LEFT"],
            pygame.K_RIGHT: DIR["RIGHT"],pygame.K_d: DIR["RIGHT"],
        }
        if key in m:
            self.snake.steer(m[key])

    # ── 更新逻辑 ──
    def update(self):
        if self.game_over or self.paused:
            return

        self.snake.move()

        # 吃食物
        if self.snake.body[0] == self.food.pos:
            self.snake.grow()
            self.score += 10 + max(0, self.eaten // 10) * 2
            self.eaten += 1
            # 粒子
            fx = self.food.pos[0] * BLOCK_SIZE + BLOCK_SIZE // 2
            fy = self.food.pos[1] * BLOCK_SIZE + BLOCK_SIZE // 2
            for _ in range(12):
                self.particles.append(Particle(fx, fy, Color.FOOD))
            self.food = Food(self.snake.body)
            # 加速
            if self.eaten % SPEED_INTERVAL == 0:
                self.speed = min(self.speed + SPEED_STEP, 25)

        # 粒子更新
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

        # 碰撞
        if self.snake.collides():
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
                self._save_high()

    # ── 绘制 ──
    def draw(self):
        self.screen.fill(Color.BG)
        self._draw_grid()
        self.food.draw(self.screen)
        self.snake.draw(self.screen)
        for p in self.particles:
            p.draw(self.screen)
        self._draw_panel()

        if self.paused:
            self._draw_overlay("⏸  暂停", Color.TEXT)
        if self.game_over:
            self._draw_overlay("💀 游戏结束", Color.FOOD,
                               f"得分: {self.score}", "按 R 重新开始 · 按 Q 退出")

        pygame.display.flip()

    def _draw_grid(self):
        for x in range(0, GRID_W * BLOCK_SIZE, BLOCK_SIZE):
            pygame.draw.line(self.screen, Color.GRID_LINE, (x, 0), (x, WIN_H))
        for y in range(0, WIN_H, BLOCK_SIZE):
            pygame.draw.line(self.screen, Color.GRID_LINE, (0, y), (GRID_W * BLOCK_SIZE, y))

    def _draw_panel(self):
        px = GRID_W * BLOCK_SIZE
        pygame.draw.rect(self.screen, Color.PANEL_BG, (px, 0, PANEL_W, WIN_H))

        labels = [
            ("🏆 分数", self.font_med, Color.TEXT, 30),
            (str(self.score), self.font_large, Color.SCORE, 70),
            ("⭐ 最高分", self.font_med, Color.TEXT, 150),
            (str(self.high_score), self.font_large, Color.FOOD, 190),
            ("⚡ 速度", self.font_med, Color.TEXT, 270),
            (f"Lv.{self.speed - INIT_SPEED + 1}", self.font_large, Color.SNAKE_HEAD, 310),
            ("🍎 已吃", self.font_med, Color.TEXT, 390),
            (str(self.eaten), self.font_large, Color.SCORE, 430),
        ]
        for text, font, color, y in labels:
            surf = font.render(text, True, color)
            self.screen.blit(surf, (px + 20, y))

        # 操作提示
        tips = [
            "── 操作 ──",
            "↑/W 上   ↓/S 下",
            "←/A 左   →/D 右",
            "P 暂停",
        ]
        y0 = 510
        for tip in tips:
            s = self.font_small.render(tip, True, Color.TEXT_DIM)
            self.screen.blit(s, (px + 15, y0))
            y0 += 22

    def _draw_overlay(self, title, title_color, subtitle=None, footer=None):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((*Color.OVERLAY, 160))
        self.screen.blit(overlay, (0, 0))

        t = self.font_large.render(title, True, title_color)
        r = t.get_rect(center=(WIN_W // 2, WIN_H // 2 - 40))
        self.screen.blit(t, r)

        if subtitle:
            s = self.font_med.render(subtitle, True, Color.TEXT)
            r2 = s.get_rect(center=(WIN_W // 2, WIN_H // 2 + 20))
            self.screen.blit(s, r2)

        if footer:
            f = self.font_small.render(footer, True, Color.TEXT_DIM)
            r3 = f.get_rect(center=(WIN_W // 2, WIN_H // 2 + 70))
            self.screen.blit(f, r3)

    # ── 主循环 ──
    def run(self):
        while True:
            if not self.handle_events():
                break
            self.update()
            self.draw()
            self.clock.tick(self.speed)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
