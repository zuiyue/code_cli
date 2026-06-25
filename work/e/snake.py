"""
贪吃蛇游戏 - 优化版
- 蛇头带眼睛，蛇身圆角过渡
- 食物闪烁动画
- 速度随分数递增
- 计分板显示当前得分和最高分
- 键盘 WASD / 方向键 双套控制
"""

import pygame
import random
import sys
from collections import deque
from dataclasses import dataclass

# ========== 配置 ==========
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 680  # 顶部留 80px 给计分板
GRID_SIZE = 20
CELL_SIZE = WINDOW_WIDTH // GRID_SIZE
FPS_BASE = 10
SCOREBOARD_HEIGHT = 80

# 颜色
BLACK = (15, 15, 20)
WHITE = (240, 240, 240)
GREEN = (80, 220, 100)
DARK_GREEN = (40, 160, 60)
RED = (240, 80, 80)
GOLD = (255, 200, 50)
GRAY = (100, 100, 120)
GRID_COLOR = (30, 30, 40)
EYE_WHITE = (255, 255, 255)
EYE_PUPIL = (20, 20, 20)

# 方向
DIRS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}


@dataclass
class GameState:
    score: int = 0
    high_score: int = 0
    game_over: bool = False
    paused: bool = False


class Snake:
    def __init__(self):
        cx, cy = GRID_SIZE // 2, GRID_SIZE // 2
        self.body = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self._grow_flag = False

    def change_direction(self, new_dir):
        # 不允许原地掉头
        if (new_dir[0] * -1, new_dir[1] * -1) != self.direction:
            self.next_direction = new_dir

    def move(self):
        self.direction = self.next_direction
        head = self.body[0]
        new_head = ((head[0] + self.direction[0]) % GRID_SIZE,
                    (head[1] + self.direction[1]) % GRID_SIZE)
        self.body.appendleft(new_head)
        if not self._grow_flag:
            self.body.pop()
        else:
            self._grow_flag = False

    def grow(self):
        self._grow_flag = True

    def collides_with_self(self):
        head = self.body[0]
        return head in list(self.body)[1:]

    def draw(self, screen):
        for i, (x, y) in enumerate(self.body):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE + SCOREBOARD_HEIGHT,
                               CELL_SIZE, CELL_SIZE)
            if i == 0:
                self._draw_head(screen, rect)
            else:
                # 蛇身渐变：越靠近尾部越暗
                ratio = 1.0 - (i / max(len(self.body), 1)) * 0.4
                color = (int(80 * ratio), int(220 * ratio), int(100 * ratio))
                pygame.draw.rect(screen, color, rect, border_radius=4)

    def _draw_head(self, screen, rect):
        pygame.draw.rect(screen, DARK_GREEN, rect, border_radius=6)
        pygame.draw.rect(screen, GREEN, rect, 2, border_radius=6)

        # 眼睛 — 根据方向定位
        dx, dy = self.direction
        cx, cy = rect.centerx, rect.centery
        # 左眼 / 右眼偏移
        if dx == 1:   # 向右
            offsets = [(-3, -4), (-3, 4)]
        elif dx == -1:  # 向左
            offsets = [(3, -4), (3, 4)]
        elif dy == -1:  # 向上
            offsets = [(-4, 3), (4, 3)]
        else:  # 向下
            offsets = [(-4, -3), (4, -3)]

        for ox, oy in offsets:
            eye_rect = pygame.Rect(0, 0, 6, 6)
            eye_rect.center = (cx + ox, cy + oy)
            pygame.draw.ellipse(screen, EYE_WHITE, eye_rect)
            pupil_rect = pygame.Rect(0, 0, 3, 3)
            pupil_rect.center = eye_rect.center
            pygame.draw.ellipse(screen, EYE_PUPIL, pupil_rect)


class Food:
    def __init__(self, snake_body):
        self.position = self._random_position(snake_body)
        self._anim_tick = 0

    def _random_position(self, snake_body):
        occupied = set(snake_body)
        while True:
            pos = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
            if pos not in occupied:
                return pos

    def draw(self, screen, tick):
        self._anim_tick += 1
        pulse = abs(pygame.math.Vector2(1, 0).rotate(self._anim_tick * 6).x) * 0.3 + 0.7
        size = int(CELL_SIZE * pulse)
        offset = (CELL_SIZE - size) // 2
        x = self.position[0] * CELL_SIZE + offset
        y = self.position[1] * CELL_SIZE + SCOREBOARD_HEIGHT + offset
        rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(screen, RED, rect, border_radius=size // 2)
        pygame.draw.rect(screen, GOLD, rect, 2, border_radius=size // 2)


def draw_scoreboard(screen, state: GameState):
    # 背景
    pygame.draw.rect(screen, (25, 25, 35), (0, 0, WINDOW_WIDTH, SCOREBOARD_HEIGHT))
    pygame.draw.line(screen, GRAY, (0, SCOREBOARD_HEIGHT), (WINDOW_WIDTH, SCOREBOARD_HEIGHT), 2)

    font = pygame.font.Font(None, 40)
    small_font = pygame.font.Font(None, 28)

    score_text = font.render(f"得分: {state.score}", True, WHITE)
    high_text = small_font.render(f"最高分: {state.high_score}", True, GOLD)

    screen.blit(score_text, (20, 20))
    screen.blit(high_text, (20, 50))

    # 右侧提示
    hint = small_font.render("WASD/方向键 移动 | 空格 暂停", True, GRAY)
    screen.blit(hint, (WINDOW_WIDTH - hint.get_width() - 20, 30))


def draw_game_over(screen, state: GameState):
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    font_big = pygame.font.Font(None, 72)
    font_mid = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 36)

    texts = [
        (font_big, "游戏结束", RED, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80)),
        (font_mid, f"得分: {state.score}", WHITE, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 10)),
        (font_mid, f"最高分: {state.high_score}", GOLD, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40)),
        (font_small, "按 R 重新开始  按 Q 退出", GRAY, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 100)),
    ]

    for font, content, color, center in texts:
        surf = font.render(content, True, color)
        rect = surf.get_rect(center=center)
        screen.blit(surf, rect)


def draw_paused(screen):
    font = pygame.font.Font(None, 56)
    text = font.render("暂停中", True, GRAY)
    rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
    screen.blit(text, rect)


def draw_grid(screen):
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (x, SCOREBOARD_HEIGHT), (x, WINDOW_HEIGHT))
    for y in range(SCOREBOARD_HEIGHT, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("贪吃蛇 🐍")
    clock = pygame.time.Clock()

    state = GameState()
    snake = Snake()
    food = Food(snake.body)
    tick = 0

    running = True
    while running:
        # ---- 事件处理 ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if state.game_over:
                    if event.key == pygame.K_r:
                        snake = Snake()
                        food = Food(snake.body)
                        state.score = 0
                        state.game_over = False
                    elif event.key == pygame.K_q:
                        running = False
                else:
                    key_map = {
                        pygame.K_UP: "UP", pygame.K_w: "UP",
                        pygame.K_DOWN: "DOWN", pygame.K_s: "DOWN",
                        pygame.K_LEFT: "LEFT", pygame.K_a: "LEFT",
                        pygame.K_RIGHT: "RIGHT", pygame.K_d: "RIGHT",
                    }
                    if event.key in key_map:
                        snake.change_direction(DIRS[key_map[event.key]])
                    elif event.key == pygame.K_SPACE:
                        state.paused = not state.paused

        # ---- 暂停 / 结束状态 ----
        if state.game_over:
            screen.fill(BLACK)
            draw_scoreboard(screen, state)
            draw_game_over(screen, state)
            pygame.display.flip()
            clock.tick(10)
            continue

        if state.paused:
            screen.fill(BLACK)
            draw_grid(screen)
            snake.draw(screen)
            food.draw(screen, tick)
            draw_scoreboard(screen, state)
            draw_paused(screen)
            pygame.display.flip()
            clock.tick(10)
            continue

        # ---- 游戏逻辑 ----
        snake.move()
        tick += 1

        # 吃食物
        if snake.body[0] == food.position:
            snake.grow()
            state.score += 1
            food = Food(snake.body)

        # 撞自己
        if snake.collides_with_self():
            state.high_score = max(state.high_score, state.score)
            state.game_over = True
            continue

        # ---- 绘制 ----
        screen.fill(BLACK)
        draw_grid(screen)
        snake.draw(screen)
        food.draw(screen, tick)
        draw_scoreboard(screen, state)

        pygame.display.flip()

        # 速度随分数递增（最快 20 FPS）
        speed = min(FPS_BASE + state.score // 3, 20)
        clock.tick(speed)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
