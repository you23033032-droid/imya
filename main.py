import arcade
import random
from collections import deque
from events import EventManager

SCREEN_WIDTH = 820
SCREEN_HEIGHT = 620
CELL_SIZE = 40
INDENT = 10

COLOR_BG = (15, 15, 25) 
COLOR_GRID = (30, 30, 50)
COLOR_SNAKE = (50, 205, 50) 
COLOR_SNAKE_HEAD = (255, 255, 255)

class GameView(arcade.View):
    def __init__(self, textures):
        super().__init__()
        
        self.rows = (SCREEN_WIDTH - 2 * INDENT) // CELL_SIZE
        self.cols = (SCREEN_HEIGHT - 2 * INDENT) // CELL_SIZE
        
        self.radius = CELL_SIZE // 2 - 4
        self.event_manager = EventManager(self.rows, self.cols)
        self.textures = textures
        

        self.sound_time_return = arcade.load_sound("time_return.mp3")
        self.music_game = arcade.load_sound("game.mp3")

            
        self.bg_music_player = None 

        self.is_rewinding = False
        self.rewind_steps_left = 0
        
        self.events = []
        self.obstacles_data = []
        
        self.setup()

    def on_show_view(self):
        if self.music_game:
            if self.bg_music_player:
                arcade.stop_sound(self.bg_music_player)
            self.bg_music_player = arcade.play_sound(self.music_game, loop=True)

    def setup(self):
        self.snake = [(self.rows // 2, self.cols // 2)]
        self.direction = (0, 1)
        self.score = 0
        self.game_over = False
        
        self.time_since_move = 0
        self.cooldown_rewind = 0.0
        self.is_rewinding = False
        self.rewind_steps_left = 0
        
        self.events = []
        self.obstacles_data = []
        
        self.history = deque(maxlen=100)
        self.history.append((self.snake.copy(), self.direction))
        
        self.apple_list = arcade.SpriteList()
        self.apple_sprite = arcade.Sprite(self.textures["apple.png"])
        self.apple_sprite.width = CELL_SIZE - 4
        self.apple_sprite.height = CELL_SIZE - 4
        self.apple_list.append(self.apple_sprite)
        
        self.spawn_apple()
        self.obstacle_list = arcade.SpriteList()

    def spawn_apple(self):
        while True:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            if (r, c) not in self.snake:
                self.apple = (r, c)
                self.apple_sprite.center_x = INDENT + r * CELL_SIZE + CELL_SIZE // 2
                self.apple_sprite.center_y = INDENT + c * CELL_SIZE + CELL_SIZE // 2
                break

    def update_obstacle_sprites(self):
        self.obstacle_list.clear()
        active_names = [e[0] for e in self.events]
        self.obstacles_data = [o for o in self.obstacles_data if o[2] in active_names]
        
        for r, c, et in self.obstacles_data:
            tex_name = self.event_manager.get_obstacle_texture_name(et)
            s = arcade.Sprite(self.textures[tex_name])
            s.width = CELL_SIZE - 2
            s.height = CELL_SIZE - 2
            s.center_x = INDENT + r * CELL_SIZE + CELL_SIZE // 2
            s.center_y = INDENT + c * CELL_SIZE + CELL_SIZE // 2
            self.obstacle_list.append(s)

    def on_key_press(self, key, modifiers):
        if self.game_over:
            if key == arcade.key.R: 
                self.setup()
            elif key == arcade.key.ESCAPE:
                if self.bg_music_player: arcade.stop_sound(self.bg_music_player)
                from menu import MenuView
                self.window.show_view(MenuView(self.textures))
            return

        if self.is_rewinding: return

        inv = 1
        if any(e[0] == 'mirror' for e in self.events): inv = -1

        if key == arcade.key.W and self.direction[1] == 0: self.direction = (0, 1 * inv)
        elif key == arcade.key.S and self.direction[1] == 0: self.direction = (0, -1 * inv)
        elif key == arcade.key.D and self.direction[0] == 0: self.direction = (1 * inv, 0)
        elif key == arcade.key.A and self.direction[0] == 0: self.direction = (-1 * inv, 0)
        elif key == arcade.key.SPACE:
            if self.cooldown_rewind <= 0 and len(self.history) > 5 and len(self.snake) > 5:
                self.time_leap()
        elif key == arcade.key.ESCAPE:
            if self.bg_music_player: arcade.stop_sound(self.bg_music_player)
            from menu import MenuView
            self.window.show_view(MenuView(self.textures))

    def time_leap(self):
        if self.sound_time_return:
            arcade.play_sound(self.sound_time_return)
            
        self.cooldown_rewind = 5.0
        self.is_rewinding = True
        self.rewind_steps_left = 5 
        
        new_ev = self.event_manager.trigger_random_event()
        self.events.append(new_ev)
        if new_ev[0] in ['red_blocks', 'stones']:
            new_obs = self.event_manager.generate_event_obstacles(new_ev[0], self.snake, self.apple)
            self.obstacles_data.extend(new_obs)
            self.update_obstacle_sprites()

    def on_update(self, delta_time):
        if self.game_over: return

        if self.is_rewinding:
            if self.rewind_steps_left > 0 and len(self.history) > 1:
                self.history.pop() 
                past_snake, past_direction = self.history[-1]
                
                self.snake = past_snake[:max(1, len(self.snake)-1)]
                
                if self.rewind_steps_left == 1:
                    self.direction = past_direction
                
                self.rewind_steps_left -= 1
            else:
                self.is_rewinding = False
            return 

        self.cooldown_rewind = max(0, self.cooldown_rewind - delta_time)
        self.time_since_move += delta_time
        
        old_ev_count = len(self.events)
        for e in self.events: e[1] -= delta_time
        self.events = [e for e in self.events if e[1] > 0]
        
        if len(self.events) < old_ev_count:
            self.update_obstacle_sprites()
            
        speed = self.event_manager.get_current_speed([e[0] for e in self.events])
        if self.time_since_move >= speed:
            self.move_snake()
            self.time_since_move = 0

    def move_snake(self):
        head = self.snake[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        
        if not (0 <= new_head[0] < self.rows and 0 <= new_head[1] < self.cols) or new_head in self.snake:
            self.game_over = True
            return

        active_names = [e[0] for e in self.events]
        hit_idx = -1
        for i, (r, c, et) in enumerate(self.obstacles_data):
            if (r, c) == new_head and et in active_names:
                if len(self.snake) <= 1:
                    self.game_over = True
                    return
                self.snake = self.event_manager.handle_obstacle_collision(et, self.snake)
                hit_idx = i
                break
                
        if hit_idx != -1:
            self.obstacles_data.pop(hit_idx)
            self.update_obstacle_sprites()
        
        self.snake.insert(0, new_head)
        if new_head == self.apple:
            self.score += 3
            self.snake.append(self.snake[-1]) 
            self.spawn_apple()
        else:
            self.snake.pop()
        
        self.history.append((self.snake.copy(), self.direction))

    def on_draw(self):
        self.clear()
        
        if self.is_rewinding:
            arcade.set_background_color((25, 25, 60))
        else:
            arcade.set_background_color(COLOR_BG)
        
        for row in range(self.rows + 1):
            x = INDENT + row * CELL_SIZE
            arcade.draw_line(x, INDENT, x, SCREEN_HEIGHT - INDENT, COLOR_GRID, 1)
        for col in range(self.cols + 1):
            y = INDENT + col * CELL_SIZE
            arcade.draw_line(INDENT, y, SCREEN_WIDTH - INDENT, y, COLOR_GRID, 1)
            
        self.apple_list.draw()
        self.obstacle_list.draw()
        
        for i, (r, c) in enumerate(self.snake):
            if self.is_rewinding:
                color = (255, 255, 255) if i == 0 else (120, 150, 255)
            else:
                color = COLOR_SNAKE_HEAD if i == 0 else COLOR_SNAKE
                
            x = INDENT + r * CELL_SIZE + CELL_SIZE // 2
            y = INDENT + c * CELL_SIZE + CELL_SIZE // 2
            rad = self.radius if i == 0 else self.radius-2
            arcade.draw_circle_filled(x, y, rad, color)
            
        arcade.draw_text(f"ОЧКИ: {self.score}", 25, SCREEN_HEIGHT - 40, arcade.color.WHITE, 14, bold=True)
        self.draw_status_text()
        self.draw_events_list()
        
        if self.game_over: self.draw_game_over_screen()

    def draw_status_text(self):
        status = "ПЕРЕМОТКА: ГОТОВО (SPACE)"
        color = arcade.color.GREEN
        if self.is_rewinding:
            status = "ВРЕМЯ ВСХПЯТЬ..."
            color = arcade.color.CYAN
        elif len(self.snake) <= 5:
            status = "ПЕРЕМОТКА: МАЛО ХВОСТА (>5)"
            color = arcade.color.GRAY
        elif self.cooldown_rewind > 0:
            status = f"ПЕРЕМОТКА: {self.cooldown_rewind:.1f}с"
            color = arcade.color.ORANGE
        arcade.draw_text(status, 25, SCREEN_HEIGHT - 70, color, 12, bold=True)

    def draw_events_list(self):
        ev_list = [f"• {e.upper()} ({d:.1f}с)" for e, d in self.events]
        arcade.draw_text("\n".join(ev_list), SCREEN_WIDTH - 220, SCREEN_HEIGHT - 40, 
                         arcade.color.AERO_BLUE, 10, bold=True, multiline=True, width=200)

    def draw_game_over_screen(self):
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (0, 0, 0, 220))
        mid_x, mid_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        arcade.draw_text("ИГРА ОКОНЧЕНА", mid_x, mid_y + 80, arcade.color.BITTERSWEET, 50, anchor_x="center", bold=True)
        arcade.draw_text(f"СЧЕТ: {self.score}", mid_x, mid_y, arcade.color.WHITE, 24, anchor_x="center")
        arcade.draw_text("R - заново | ESC - меню", mid_x, mid_y - 80, arcade.color.LIGHT_GRAY, 16, anchor_x="center")