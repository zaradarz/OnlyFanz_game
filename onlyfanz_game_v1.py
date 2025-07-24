import pygame
import random
import os
import sys


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
BAD_OBJECTS = ["ac", "heater"]   # Game over if caught
ALL_OBJECTS = GOOD_OBJECTS + BAD_OBJECTS

# High Score storage file
HIGH_SCORE_FILE = "only_fanz_highscore.txt"

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
try:
    collect_sound = pygame.mixer.Sound("collect.wav")
    lose_sound = pygame.mixer.Sound("lose.wav")
except pygame.error as e:
    print(f"Could not load sound: {e}")
    sys.exit()

# (Optional) Adjust volume: range 0.0 (mute) to 1.0 (full)
collect_sound.set_volume(0.6)
lose_sound.set_volume(0.6)

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

ASSETS = {
    "fan": fan_img,
    "ac": ac_img,
    "heater": heater_img
}

# Scale the assets:
ASSETS["fan"] = pygame.transform.scale(ASSETS["fan"], (50, 50))
ASSETS["ac"] = pygame.transform.scale(ASSETS["ac"], (50, 50))
ASSETS["heater"] = pygame.transform.scale(ASSETS["heater"], (50, 50))

# -----------------------------
# Fonts
# -----------------------------
font = pygame.font.SysFont("Arial", 28, bold=True)
small_font = pygame.font.SysFont("Arial", 22, bold=True)

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
    Represents a falling object (fan/ac/heater) that has:
      - image
      - position
      - falling speed
      - type (which determines good vs. bad)
    """
    def __init__(self, obj_type, x, y, speed):
        self.obj_type = obj_type
        self.image = ASSETS[obj_type]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.speed = speed

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        surface.blit(self.image, self.rect)

def check_collision(obj_rect, player_rect):
    return obj_rect.colliderect(player_rect)

def main_game():
    # Player initial position
    player_x = SCREEN_WIDTH // 2
    player_y = SCREEN_HEIGHT - 150

    # Score and high score
    score = 0
    high_score = load_high_score()

    # Falling objects list
    falling_objects = []

    # Timers for object spawning & difficulty
    object_spawn_timer = 0
    difficulty_timer = 0

    # Dynamic fall speed & spawn interval
    fall_speed = OBJECT_FALL_SPEED_START
    spawn_interval = OBJECT_SPAWN_INTERVAL

    # Game loop
    running = True
    while running:
        dt = clock.tick(FPS)
        screen.fill((200, 220, 255))  # Light background color

        # 1. Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. Player input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player_x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            player_x += PLAYER_SPEED

        # Keep player within screen bounds
        player_x = max(0, min(player_x, SCREEN_WIDTH - ZARA_WIDTH))

        player_rect = pygame.Rect(player_x, player_y, ZARA_WIDTH, ZARA_HEIGHT)

        # 3. Spawn new falling objects
        object_spawn_timer += dt
        if object_spawn_timer >= spawn_interval:
            object_spawn_timer = 0
            chosen_type = random.choice(ALL_OBJECTS)
            x_pos = random.randint(0, SCREEN_WIDTH - 50)  # Adjust for object width
            falling_objects.append(FallingObject(chosen_type, x_pos, -50, fall_speed))

        # 4. Increase difficulty over time
        difficulty_timer += dt
        if difficulty_timer >= DIFFICULTY_INCREASE_INTERVAL:
            difficulty_timer = 0
            fall_speed = min(fall_speed + SPEED_INCREMENT, OBJECT_FALL_SPEED_MAX)
            spawn_interval = max(spawn_interval - INTERVAL_DECREMENT, 200)

        # 5. Update objects & check collisions
        objects_to_remove = []
        for obj in falling_objects:
            obj.update()

            if check_collision(obj.rect, player_rect):
                # Collision
                if obj.obj_type == "fan":
                    # Good catch
                    collect_sound.play()     # <-- Play the 'collect' sound
                    score += 1
                    objects_to_remove.append(obj)
                else:
                    # Bad catch -> Game Over
                    lose_sound.play()       # <-- Play the 'lose' sound
                    if score > high_score:
                        save_high_score(score)
                    game_over_screen(score)
                    return  # Exit this game, return to start screen

            # Remove object if it goes off screen
            if obj.rect.y > SCREEN_HEIGHT:
                objects_to_remove.append(obj)

        # Cleanup
        for obj in objects_to_remove:
            if obj in falling_objects:
                falling_objects.remove(obj)

        # 6. Draw everything
        # Draw falling objects
        for obj in falling_objects:
            obj.draw(screen)

        # Draw Zara
        screen.blit(zara_img, (player_x, player_y))

        # Draw score
        score_text = small_font.render(f"Score: {score}", True, (0, 0, 0))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 10))

        # Draw high score
        high_score_text = small_font.render(f"High Score: {max(score, high_score)}", True, (0, 0, 0))
        screen.blit(high_score_text, (10, 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

def game_over_screen(score):
    # Overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((50, 50, 50))
    screen.blit(overlay, (0,0))

    text1 = font.render("You caught the wrong thing :(", True, (255, 0, 0))
    text2 = font.render(f"Final Score: {score}", True, (255, 255, 255))
    text3 = small_font.render("Press [SPACE] to Try Again or [ESC] to Quit", True, (255, 255, 255))

    screen.blit(text1, (SCREEN_WIDTH//2 - text1.get_width()//2, SCREEN_HEIGHT//2 - 60))
    screen.blit(text2, (SCREEN_WIDTH//2 - text2.get_width()//2, SCREEN_HEIGHT//2))
    screen.blit(text3, (SCREEN_WIDTH//2 - text3.get_width()//2, SCREEN_HEIGHT//2 + 40))

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

def start_screen():
    screen.fill((200,220,255))

    title_text = font.render("Only-Fanz - by Zara Dar", True, (0,0,0))
    play_text = small_font.render("Press [SPACE] to Play", True, (0,0,0))
    high_score = load_high_score()
    high_score_text = small_font.render(f"High Score: {high_score}", True, (0,0,0))

    screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, SCREEN_HEIGHT//2 - 60))
    screen.blit(play_text, (SCREEN_WIDTH//2 - play_text.get_width()//2, SCREEN_HEIGHT//2))
    screen.blit(high_score_text, (SCREEN_WIDTH//2 - high_score_text.get_width()//2, SCREEN_HEIGHT//2 + 40))

    pygame.display.flip()

    waiting = True
    while waiting:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False

def main():
    while True:
        start_screen()
        main_game()

if __name__ == "__main__":
    main()
