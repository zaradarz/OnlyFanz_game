import pygame
import random
import os
import sys
import math


# -----------------------------
# Game Configuration Constants
# -----------------------------
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 640
FPS = 60

# Player
PLAYER_SPEED = 5
ZARA_WIDTH = 46
ZARA_HEIGHT = 140

# Falling Objects
OBJECT_FALL_SPEED_START = 2  # initial speed of falling objects
OBJECT_FALL_SPEED_MAX = 15   # maximum fall speed
OBJECT_SPAWN_INTERVAL = 800  # milliseconds between spawns at the beginning

# Difficulty ramp (accelerates falling speed / faster spawns)
DIFFICULTY_INCREASE_INTERVAL = 5000  # every 5 seconds
SPEED_INCREMENT = 0.3
INTERVAL_DECREMENT = 50

# Object types
GOOD_OBJECTS = ["fan"]           # +1 point if caught
BAD_OBJECTS = ["ac", "heater"]   # Lose a life if caught
POWERUP_OBJECTS = [
    "shield", "slow_motion", "double_points", "magnet",
    "bomb", "speed_boost", "invisibility"
]  # Power-ups
ALL_OBJECTS = GOOD_OBJECTS + BAD_OBJECTS + POWERUP_OBJECTS

# Power-up durations (in milliseconds)
POWERUP_DURATION = 5000  # 5 seconds

# High Score storage file
HIGH_SCORE_FILE = "only_fanz_highscore.txt"

# Game Modes
GAME_MODES = [
    {"name": "Classic", "desc": "Normal fan-catching game", "lives": 3, "speed": 1.0, "powerups": True},
    {"name": "Chill", "desc": "Slower speed, no power-ups", "lives": 3, "speed": 0.7, "powerups": False},
    {"name": "Hardcore", "desc": "Fast speed, only 1 life", "lives": 1, "speed": 1.5, "powerups": False},
    {"name": "Memory", "desc": "Items fall in a pattern; remember & react", "lives": 3, "speed": 1.0, "powerups": False},
]

# -----------------------------
# Initialize Pygame
# -----------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Only-Fanz - by Zara Dar")
clock = pygame.time.Clock()

# -----------------------------
# Load Sound Effects
# -----------------------------
collect_sound = None
lose_sound = None

try:
    pygame.mixer.init()  # Initialize the mixer for sound
    collect_sound = pygame.mixer.Sound("collect.wav")
    lose_sound = pygame.mixer.Sound("lose.wav")
    # (Optional) Adjust volume: range 0.0 (mute) to 1.0 (full)
    collect_sound.set_volume(0.6)
    lose_sound.set_volume(0.6)
except pygame.error as e:
    print(f"Could not load sound: {e}")
    print("Game will run without sound effects.")

# -----------------------------
# Load Images
# -----------------------------
# 1) Zara (transparent background PNG)
try:
    zara_img = pygame.image.load("zara.png").convert_alpha()
    zara_img = pygame.transform.scale(zara_img, (ZARA_WIDTH, ZARA_HEIGHT))
except pygame.error:
    print("Could not load zara.png. Please ensure the file is in the same folder.")
    sys.exit()


# 2) Falling Objects (fan, ac, heater)
try:
    fan_img = pygame.image.load("fan.png").convert_alpha()
    ac_img = pygame.image.load("ac.png").convert_alpha()
    heater_img = pygame.image.load("heater.png").convert_alpha()
except pygame.error as e:
    print("One of fan.png, ac.png, or heater.png could not be loaded. Check files.")
    sys.exit()


# Heart image for lives
try:
    heart_img = pygame.image.load("heart.png").convert_alpha()
    heart_img = pygame.transform.scale(heart_img, (32, 32))
except pygame.error as e:
    print("Could not load heart.png. Please ensure the file is in the same folder.")
    heart_img = None

# Sun and Moon images for background
try:
    sun_img = pygame.image.load("sun.png").convert_alpha()
    sun_img = pygame.transform.scale(sun_img, (80, 80))
except pygame.error as e:
    print("Could not load sun.png. Please ensure the file is in the same folder.")
    sun_img = None
try:
    moon_img = pygame.image.load("moon.png").convert_alpha()
    moon_img = pygame.transform.scale(moon_img, (80, 80))
except pygame.error as e:
    print("Could not load moon.png. Please ensure the file is in the same folder.")
    moon_img = None

ASSETS = {
    "fan": fan_img,
    "ac": ac_img,
    "heater": heater_img,
    "heart": heart_img,
    "sun": sun_img,
    "moon": moon_img
}

# Scale the assets:
ASSETS["fan"] = pygame.transform.scale(ASSETS["fan"], (50, 50))
ASSETS["ac"] = pygame.transform.scale(ASSETS["ac"], (50, 50))
ASSETS["heater"] = pygame.transform.scale(ASSETS["heater"], (50, 50))

# Create power-up images (colored circles or icons)
def create_powerup_image(color, size=50, symbol=None, symbol_color=(0,0,0)):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, color, (size//2, size//2), size//2)
    if symbol:
        font_icon = pygame.font.SysFont("Arial", 28, bold=True)
        text = font_icon.render(symbol, True, symbol_color)
        rect = text.get_rect(center=(size//2, size//2))
        surface.blit(text, rect)
    return surface

ASSETS["shield"] = create_powerup_image((0, 255, 255))  # Cyan
ASSETS["slow_motion"] = create_powerup_image((255, 255, 0))  # Yellow
ASSETS["double_points"] = create_powerup_image((255, 0, 255))  # Magenta
ASSETS["magnet"] = create_powerup_image((0, 255, 0))  # Green
ASSETS["bomb"] = create_powerup_image((255, 0, 0), symbol="💣", symbol_color=(255,255,255))  # Red
ASSETS["speed_boost"] = create_powerup_image((255, 140, 0), symbol="💨", symbol_color=(255,255,255))  # Orange
ASSETS["invisibility"] = create_powerup_image((255, 255, 255), symbol="★", symbol_color=(0,0,0))  # White

# -----------------------------
# Fonts
# -----------------------------
font = pygame.font.SysFont("Arial", 28, bold=True)
small_font = pygame.font.SysFont("Arial", 22, bold=True)
tiny_font = pygame.font.SysFont("Arial", 16, bold=True)

# -----------------------------
# Particle System
# -----------------------------
class Particle:
    def __init__(self, x, y, color, velocity_x, velocity_y, life=30):
        self.x = x
        self.y = y
        self.color = color
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.velocity_y += 0.2  # Gravity
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            color_with_alpha = (*self.color, alpha)
            size = max(1, int(3 * (self.life / self.max_life)))
            pygame.draw.circle(surface, color_with_alpha, (int(self.x), int(self.y)), size)

# -----------------------------
# Load / Save High Score
# -----------------------------
def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        with open(HIGH_SCORE_FILE, 'r') as f:
            try:
                return int(f.read())
            except ValueError:
                return 0
    return 0

def save_high_score(score):
    with open(HIGH_SCORE_FILE, 'w') as f:
        f.write(str(score))

# -----------------------------
# Game Objects & Mechanics
# -----------------------------
class FallingObject:
    """
    Represents a falling object (fan/ac/heater/powerup) that has:
      - image
      - position
      - falling speed
      - type (which determines good vs. bad vs. powerup)
    """
    def __init__(self, obj_type, x, y, speed):
        self.obj_type = obj_type
        self.image = ASSETS[obj_type]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.speed = speed
        self.rotation = 0
        self.rotation_speed = random.uniform(-2, 2)

    def update(self):
        self.rect.y += self.speed
        self.rotation += self.rotation_speed

    def draw(self, surface):
        # Rotate the image
        rotated_image = pygame.transform.rotate(self.image, self.rotation)
        rotated_rect = rotated_image.get_rect(center=self.rect.center)
        surface.blit(rotated_image, rotated_rect)

def check_collision(obj_rect, player_rect):
    return obj_rect.colliderect(player_rect)

def create_particles(x, y, color, count=10):
    particles = []
    for _ in range(count):
        vel_x = random.uniform(-3, 3)
        vel_y = random.uniform(-5, -1)
        particles.append(Particle(x, y, color, vel_x, vel_y))
    return particles

def main_game(selected_mode):
    # Player initial position
    player_x = SCREEN_WIDTH // 2
    player_y = SCREEN_HEIGHT - 150

    # Score and high score
    score = 0
    high_score = load_high_score()
    combo = 0
    max_combo = 0

    # Falling objects list
    falling_objects = []

    # Timers for object spawning & difficulty
    object_spawn_timer = 0
    difficulty_timer = 0

    # Dynamic fall speed & spawn interval
    fall_speed = OBJECT_FALL_SPEED_START * selected_mode["speed"]
    spawn_interval = OBJECT_SPAWN_INTERVAL

    # Power-up system
    active_powerups = {}
    powerup_timers = {}
    magnet_active = False
    shield_active = False
    slow_motion_active = False
    double_points_active = False
    speed_boost_active = False
    invisibility_active = False
    speed_boost_end = 0
    invisibility_end = 0

    # Particle system
    particles = []

    # Lives system
    lives = selected_mode["lives"]
    max_lives = lives

    # Game levels
    level = 1
    next_level_score = 20

    # Day/Night background system
    DAY_LENGTH = 40_000  # ms for full day-night cycle (40s)
    NIGHT_LENGTH = 40_000
    CYCLE_LENGTH = DAY_LENGTH + NIGHT_LENGTH
    cycle_start_time = pygame.time.get_ticks()
    # Star field
    num_stars = 60
    stars = []
    for _ in range(num_stars):
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, SCREEN_HEIGHT//2)
        base_brightness = random.randint(180, 255)
        twinkle_speed = random.uniform(0.5, 2.0)
        stars.append({"x": x, "y": y, "base": base_brightness, "twinkle": twinkle_speed, "phase": random.uniform(0, 2*math.pi)})

    running = True
    paused = False
    while running:
        dt = clock.tick(FPS)
        # Handle events (pause/resume always checked)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if not paused and event.key == pygame.K_p:
                    paused = True
                elif paused and event.key == pygame.K_r:
                    paused = False

        if paused:
            # Draw paused overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            pause_text = font.render("Game Paused", True, (255, 255, 255))
            instruct_text = small_font.render("Press R to resume", True, (255, 255, 255))
            pause_menu_text = tiny_font.render("Pause / Resume Menu", True, (255,255,255))
            pause_keys_text = tiny_font.render("Press P to pause, R to resume.", True, (255,255,255))
            screen.blit(pause_text, (SCREEN_WIDTH//2 - pause_text.get_width()//2, SCREEN_HEIGHT//2 - 60))
            screen.blit(instruct_text, (SCREEN_WIDTH//2 - instruct_text.get_width()//2, SCREEN_HEIGHT//2 - 10))
            screen.blit(pause_menu_text, (SCREEN_WIDTH//2 - pause_menu_text.get_width()//2, SCREEN_HEIGHT//2 + 40))
            screen.blit(pause_keys_text, (SCREEN_WIDTH//2 - pause_keys_text.get_width()//2, SCREEN_HEIGHT//2 + 70))
            pygame.display.flip()
            continue

        # Apply slow motion effect
        if slow_motion_active:
            dt = dt // 2
        # Speed boost effect
        current_time = pygame.time.get_ticks()
        if speed_boost_active and current_time > speed_boost_end:
            speed_boost_active = False
        if invisibility_active and current_time > invisibility_end:
            invisibility_active = False

        # Level up every 20 points
        if score >= next_level_score:
            level += 1
            next_level_score += 20
            # Increase speed a bit more for each level
            fall_speed = min(fall_speed + 0.7, OBJECT_FALL_SPEED_MAX)
            # Optionally, decrease spawn interval for more chaos
            spawn_interval = max(spawn_interval - 40, 120)


        # --- Dynamic Day/Night Background ---
        now = pygame.time.get_ticks()
        t = ((now - cycle_start_time) % CYCLE_LENGTH) / CYCLE_LENGTH
        # t: 0.0-0.5 = day, 0.5-1.0 = night
        if t < 0.5:
            # Day
            day_progress = t / 0.5
            # Sky blue gradient
            top_color = (135, 206, 250)
            bottom_color = (255, 255, 255)
            # Interpolate for smooth transition to night
            interp = day_progress
            sky_top = tuple(int(top_color[i]*(1-interp) + 20*interp) for i in range(3))
            sky_bottom = tuple(int(bottom_color[i]*(1-interp) + 40*interp) for i in range(3))
            for y in range(SCREEN_HEIGHT):
                ratio = y / SCREEN_HEIGHT
                r = int(sky_top[0]*(1-ratio) + sky_bottom[0]*ratio)
                g = int(sky_top[1]*(1-ratio) + sky_bottom[1]*ratio)
                b = int(sky_top[2]*(1-ratio) + sky_bottom[2]*ratio)
                pygame.draw.line(screen, (r,g,b), (0,y), (SCREEN_WIDTH,y))
            # Sun arc
            if ASSETS["sun"]:
                sun_angle = math.pi * (1 - day_progress)  # left to right
                sun_x = int(SCREEN_WIDTH//2 + math.cos(sun_angle)*220)
                sun_y = int(SCREEN_HEIGHT//2 - math.sin(sun_angle)*180)
                screen.blit(ASSETS["sun"], (sun_x-40, sun_y-40))
            # Optionally: clouds (simple ellipses)
            for i in range(3):
                cx = 100 + i*180 + int(30*math.sin(now/2000 + i))
                cy = 100 + 20*i
                pygame.draw.ellipse(screen, (255,255,255,180), (cx, cy, 80, 40))
        else:
            # Night
            night_progress = (t-0.5)/0.5
            # Night sky gradient
            top_color = (20, 24, 60)
            bottom_color = (40, 40, 80)
            interp = night_progress
            sky_top = tuple(int(top_color[i]*(interp) + 10*(1-interp)) for i in range(3))
            sky_bottom = tuple(int(bottom_color[i]*(interp) + 20*(1-interp)) for i in range(3))
            for y in range(SCREEN_HEIGHT):
                ratio = y / SCREEN_HEIGHT
                r = int(sky_top[0]*(1-ratio) + sky_bottom[0]*ratio)
                g = int(sky_top[1]*(1-ratio) + sky_bottom[1]*ratio)
                b = int(sky_top[2]*(1-ratio) + sky_bottom[2]*ratio)
                pygame.draw.line(screen, (r,g,b), (0,y), (SCREEN_WIDTH,y))
            # Moon arc
            if ASSETS["moon"]:
                moon_angle = math.pi * (1 - night_progress)
                moon_x = int(SCREEN_WIDTH//2 + math.cos(moon_angle)*220)
                moon_y = int(SCREEN_HEIGHT//2 - math.sin(moon_angle)*180)
                screen.blit(ASSETS["moon"], (moon_x-40, moon_y-40))
            # Stars (twinkle)
            for star in stars:
                phase = now/1000*star["twinkle"] + star["phase"]
                brightness = int(star["base"] + 50*math.sin(phase))
                color = (brightness, brightness, brightness)
                pygame.draw.circle(screen, color, (star["x"], star["y"]), 2)

        # 2. Player input
        keys = pygame.key.get_pressed()
        player_speed = PLAYER_SPEED * (2 if speed_boost_active else 1)
        if keys[pygame.K_LEFT]:
            player_x -= player_speed
        if keys[pygame.K_RIGHT]:
            player_x += player_speed

        # Keep player within screen bounds
        player_x = max(0, min(player_x, SCREEN_WIDTH - ZARA_WIDTH))

        player_rect = pygame.Rect(player_x, player_y, ZARA_WIDTH, ZARA_HEIGHT)

        # 3. Spawn new falling objects
        object_spawn_timer += dt
        if object_spawn_timer >= spawn_interval:
            object_spawn_timer = 0
            if selected_mode["powerups"]:
                if random.random() < 0.8:
                    chosen_type = random.choice(GOOD_OBJECTS + BAD_OBJECTS)
                else:
                    chosen_type = random.choice(POWERUP_OBJECTS)
            else:
                chosen_type = random.choice(GOOD_OBJECTS + BAD_OBJECTS)
            x_pos = random.randint(0, SCREEN_WIDTH - 50)
            falling_objects.append(FallingObject(chosen_type, x_pos, -50, fall_speed))

        # 4. Increase difficulty over time (still ramps up)
        difficulty_timer += dt
        if difficulty_timer >= DIFFICULTY_INCREASE_INTERVAL:
            difficulty_timer = 0
            fall_speed = min(fall_speed + SPEED_INCREMENT, OBJECT_FALL_SPEED_MAX)
            spawn_interval = max(spawn_interval - INTERVAL_DECREMENT, 200)

        # 5. Update power-up timers
        current_time = pygame.time.get_ticks()
        expired_powerups = []
        for powerup, start_time in powerup_timers.items():
            if current_time - start_time > POWERUP_DURATION:
                expired_powerups.append(powerup)
        for powerup in expired_powerups:
            del powerup_timers[powerup]
            if powerup == "shield":
                shield_active = False
            elif powerup == "slow_motion":
                slow_motion_active = False
            elif powerup == "double_points":
                double_points_active = False
            elif powerup == "magnet":
                magnet_active = False

        # 6. Update objects & check collisions
        objects_to_remove = []
        for obj in falling_objects:
            obj.update()
            if magnet_active and obj.obj_type == "fan":
                if obj.rect.x < player_x:
                    obj.rect.x += 2
                elif obj.rect.x > player_x:
                    obj.rect.x -= 2
            # Invisibility: skip all collisions
            if invisibility_active:
                continue
            if check_collision(obj.rect, player_rect):
                if obj.obj_type == "fan":
                    if collect_sound:
                        collect_sound.play()
                    points = 2 if double_points_active else 1
                    score += points
                    combo += 1
                    if combo > max_combo:
                        max_combo = combo
                    if combo >= 5:
                        bonus = combo // 5
                        score += bonus
                    particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (0, 255, 0), 15))
                    objects_to_remove.append(obj)
                elif obj.obj_type in POWERUP_OBJECTS:
                    if collect_sound:
                        collect_sound.play()
                    powerup_timers[obj.obj_type] = current_time
                    if obj.obj_type == "shield":
                        shield_active = True
                    elif obj.obj_type == "slow_motion":
                        slow_motion_active = True
                    elif obj.obj_type == "double_points":
                        double_points_active = True
                    elif obj.obj_type == "magnet":
                        magnet_active = True
                    elif obj.obj_type == "bomb":
                        # Bomb: destroy all bad objects on screen
                        for bad in [o for o in falling_objects if o.obj_type in BAD_OBJECTS]:
                            particles.extend(create_particles(bad.rect.centerx, bad.rect.centery, (255,0,0), 20))
                            if bad not in objects_to_remove:
                                objects_to_remove.append(bad)
                    elif obj.obj_type == "speed_boost":
                        speed_boost_active = True
                        speed_boost_end = current_time + 5000
                    elif obj.obj_type == "invisibility":
                        invisibility_active = True
                        invisibility_end = current_time + 5000
                    particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (255, 255, 0), 20))
                    objects_to_remove.append(obj)
                else:
                    if shield_active:
                        if lose_sound:
                            lose_sound.play()
                        particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (0, 255, 255), 25))
                        objects_to_remove.append(obj)
                        shield_active = False
                        if "shield" in powerup_timers:
                            del powerup_timers["shield"]
                    else:
                        if lose_sound:
                            lose_sound.play()
                        particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (255, 0, 0), 30))
                        lives -= 1
                        objects_to_remove.append(obj)
                        if lives <= 0:
                            if score > high_score:
                                save_high_score(score)
                            game_over_screen(score, max_combo)
                            return
            if obj.rect.y > SCREEN_HEIGHT:
                if obj.obj_type == "fan":
                    combo = 0
                objects_to_remove.append(obj)
        for obj in objects_to_remove:
            if obj in falling_objects:
                falling_objects.remove(obj)
        particles = [p for p in particles if p.life > 0]
        for particle in particles:
            particle.update()
        for obj in falling_objects:
            obj.draw(screen)
        for particle in particles:
            particle.draw(screen)
        if shield_active:
            shield_surface = pygame.Surface((ZARA_WIDTH + 20, ZARA_HEIGHT + 20), pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surface, (0, 255, 255, 100), (0, 0, ZARA_WIDTH + 20, ZARA_HEIGHT + 20))
            screen.blit(shield_surface, (player_x - 10, player_y - 10))
        screen.blit(zara_img, (player_x, player_y))
        # Draw UI
        score_text = small_font.render(f"Score: {score}", True, (0, 0, 0))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 10))
        high_score_text = small_font.render(f"High Score: {max(score, high_score)}", True, (0, 0, 0))
        screen.blit(high_score_text, (10, 10))
        # Draw lives as heart images
        for i in range(lives):
            x = SCREEN_WIDTH-40-30*i
            y = 10
            if ASSETS["heart"]:
                screen.blit(ASSETS["heart"], (x, y))
            else:
                # fallback: draw a red heart shape
                points = [
                    (x+12, y+30),
                    (x, y+15),
                    (x+6, y),
                    (x+12, y+8),
                    (x+18, y),
                    (x+24, y+15),
                ]
                pygame.draw.polygon(screen, (255,0,0), points)
                pygame.draw.circle(screen, (255,0,0), (x+8, y+12), 8)
                pygame.draw.circle(screen, (255,0,0), (x+16, y+12), 8)
        # Draw level
        level_text = small_font.render(f"Level: {level}", True, (0,0,128))
        screen.blit(level_text, (SCREEN_WIDTH//2 - level_text.get_width()//2, 40))
        if combo > 1:
            combo_text = small_font.render(f"Combo: {combo}x", True, (255, 0, 0))
            screen.blit(combo_text, (SCREEN_WIDTH - combo_text.get_width() - 10, 70))
        y_offset = 100
        # Power-up indicators with timers
        if shield_active:
            shield_text = tiny_font.render("SHIELD", True, (0, 255, 255))
            screen.blit(shield_text, (10, y_offset))
            y_offset += 20
        if slow_motion_active:
            slow_text = tiny_font.render("SLOW MOTION", True, (255, 255, 0))
            screen.blit(slow_text, (10, y_offset))
            y_offset += 20
        if double_points_active:
            double_text = tiny_font.render("DOUBLE POINTS", True, (255, 0, 255))
            screen.blit(double_text, (10, y_offset))
            y_offset += 20
        if magnet_active:
            magnet_text = tiny_font.render("MAGNET", True, (0, 255, 0))
            screen.blit(magnet_text, (10, y_offset))
            y_offset += 20
        if speed_boost_active:
            time_left = max(0, (speed_boost_end - pygame.time.get_ticks())//1000)
            speed_text = tiny_font.render(f"SPEED BOOST: {time_left}s", True, (255, 140, 0))
            screen.blit(speed_text, (10, y_offset))
            y_offset += 20
        if invisibility_active:
            time_left = max(0, (invisibility_end - pygame.time.get_ticks())//1000)
            invis_text = tiny_font.render(f"INVISIBLE: {time_left}s", True, (128,128,128))
            screen.blit(invis_text, (10, y_offset))
            y_offset += 20
        pygame.display.flip()
    pygame.quit()
    sys.exit()

def game_over_screen(score, max_combo):
    # Overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((50, 50, 50))
    screen.blit(overlay, (0,0))

    text1 = font.render("You caught the wrong thing :(", True, (255, 0, 0))
    text2 = font.render(f"Final Score: {score}", True, (255, 255, 255))
    text3 = small_font.render(f"Max Combo: {max_combo}x", True, (255, 255, 255))
    text4 = small_font.render("Press [SPACE] to Try Again or [ESC] to Quit", True, (255, 255, 255))

    screen.blit(text1, (SCREEN_WIDTH//2 - text1.get_width()//2, SCREEN_HEIGHT//2 - 80))
    screen.blit(text2, (SCREEN_WIDTH//2 - text2.get_width()//2, SCREEN_HEIGHT//2 - 40))
    screen.blit(text3, (SCREEN_WIDTH//2 - text3.get_width()//2, SCREEN_HEIGHT//2))
    screen.blit(text4, (SCREEN_WIDTH//2 - text4.get_width()//2, SCREEN_HEIGHT//2 + 40))

    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

def mode_select_screen():
    selected = 0
    high_score = load_high_score()
    while True:
        screen.fill((200,220,255))
        title_text = font.render("Only-Fanz V3", True, (0,0,0))
        subtitle_text = small_font.render("by Zara Dar", True, (0,0,0))
        high_score_text = small_font.render(f"High Score: {high_score}", True, (0,0,0))
        screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, 60))
        screen.blit(subtitle_text, (SCREEN_WIDTH//2 - subtitle_text.get_width()//2, 110))
        screen.blit(high_score_text, (SCREEN_WIDTH//2 - high_score_text.get_width()//2, 150))
        mode_title = small_font.render("Select Game Mode:", True, (0,0,0))
        screen.blit(mode_title, (SCREEN_WIDTH//2 - mode_title.get_width()//2, 200))
        for i, mode in enumerate(GAME_MODES):
            color = (0,0,0) if i != selected else (0,128,255)
            mode_text = small_font.render(f"{mode['name']}: {mode['desc']}", True, color)
            screen.blit(mode_text, (SCREEN_WIDTH//2 - mode_text.get_width()//2, 240 + i*40))
        instruct = tiny_font.render("Use UP/DOWN, ENTER to select", True, (0,0,0))
        screen.blit(instruct, (SCREEN_WIDTH//2 - instruct.get_width()//2, 420))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(GAME_MODES)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(GAME_MODES)
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    return GAME_MODES[selected]

def main():
    while True:
        selected_mode = mode_select_screen()
        main_game(selected_mode)

if __name__ == "__main__":
    main()
