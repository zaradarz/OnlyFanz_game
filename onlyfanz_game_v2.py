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
BAD_OBJECTS = ["ac", "heater"]   # Game over if caught
POWERUP_OBJECTS = ["shield", "slow_motion", "double_points", "magnet"]  # Power-ups
ALL_OBJECTS = GOOD_OBJECTS + BAD_OBJECTS + POWERUP_OBJECTS

# Power-up durations (in milliseconds)
POWERUP_DURATION = 5000  # 5 seconds

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

ASSETS = {
    "fan": fan_img,
    "ac": ac_img,
    "heater": heater_img
}

# Scale the assets:
ASSETS["fan"] = pygame.transform.scale(ASSETS["fan"], (50, 50))
ASSETS["ac"] = pygame.transform.scale(ASSETS["ac"], (50, 50))
ASSETS["heater"] = pygame.transform.scale(ASSETS["heater"], (50, 50))

# Create power-up images (colored circles for now)
def create_powerup_image(color, size=50):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, color, (size//2, size//2), size//2)
    return surface

ASSETS["shield"] = create_powerup_image((0, 255, 255))  # Cyan
ASSETS["slow_motion"] = create_powerup_image((255, 255, 0))  # Yellow
ASSETS["double_points"] = create_powerup_image((255, 0, 255))  # Magenta
ASSETS["magnet"] = create_powerup_image((0, 255, 0))  # Green

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

def check_collision(obj_rect, player_rect, obj_image=None, player_image=None):
    """
    Check pixel-perfect collision between two objects.
    Only non-transparent pixels (alpha > 127) count as collision.
    Falls back to rectangle collision if images are not provided.
    """
    if not obj_rect.colliderect(player_rect):
        return False
    
    if obj_image is None or player_image is None:
        return True
    
    # Calculate overlap area
    overlap_rect = obj_rect.clip(player_rect)
    
    for x in range(overlap_rect.width):
        for y in range(overlap_rect.height):
            # Calculate pixel positions in both images
            obj_x = overlap_rect.x - obj_rect.x + x
            obj_y = overlap_rect.y - obj_rect.y + y
            player_x = overlap_rect.x - player_rect.x + x
            player_y = overlap_rect.y - player_rect.y + y
            
            if (0 <= obj_x < obj_image.get_width() and 0 <= obj_y < obj_image.get_height() and
                0 <= player_x < player_image.get_width() and 0 <= player_y < player_image.get_height()):
                
                obj_alpha = obj_image.get_at((obj_x, obj_y))[3]
                player_alpha = player_image.get_at((player_x, player_y))[3]
                
                if obj_alpha > 127 and player_alpha > 127:
                    return True
    
    return False

def create_particles(x, y, color, count=10):
    particles = []
    for _ in range(count):
        vel_x = random.uniform(-3, 3)
        vel_y = random.uniform(-5, -1)
        particles.append(Particle(x, y, color, vel_x, vel_y))
    return particles

def main_game():
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
    fall_speed = OBJECT_FALL_SPEED_START
    spawn_interval = OBJECT_SPAWN_INTERVAL

    # Power-up system
    active_powerups = {}
    powerup_timers = {}
    magnet_active = False
    shield_active = False
    slow_motion_active = False
    double_points_active = False

    # Particle system
    particles = []

    # Game loop
    running = True
    while running:
        dt = clock.tick(FPS)
        
        # Apply slow motion effect
        if slow_motion_active:
            dt = dt // 2
        
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
            
            # Spawn regular objects
            if random.random() < 0.8:  # 80% chance for regular objects
                chosen_type = random.choice(GOOD_OBJECTS + BAD_OBJECTS)
            else:  # 20% chance for power-ups
                chosen_type = random.choice(POWERUP_OBJECTS)
            
            x_pos = random.randint(0, SCREEN_WIDTH - 50)
            falling_objects.append(FallingObject(chosen_type, x_pos, -50, fall_speed))

        # 4. Increase difficulty over time
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

            # Magnet effect
            if magnet_active and obj.obj_type == "fan":
                # Move fans towards player
                if obj.rect.x < player_x:
                    obj.rect.x += 2
                elif obj.rect.x > player_x:
                    obj.rect.x -= 2

            if check_collision(obj.rect, player_rect, obj.image, zara_img):
                # Collision
                if obj.obj_type == "fan":
                    # Good catch
                    if collect_sound:
                        collect_sound.play()
                    
                    # Calculate points (with double points power-up)
                    points = 2 if double_points_active else 1
                    score += points
                    
                    # Combo system
                    combo += 1
                    if combo > max_combo:
                        max_combo = combo
                    
                    # Bonus points for combo
                    if combo >= 5:
                        bonus = combo // 5
                        score += bonus
                    
                    # Create particles
                    particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (0, 255, 0), 15))
                    
                    objects_to_remove.append(obj)
                    
                elif obj.obj_type in POWERUP_OBJECTS:
                    # Power-up collected
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
                    
                    # Create particles
                    particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (255, 255, 0), 20))
                    
                    objects_to_remove.append(obj)
                    
                else:
                    # Bad catch
                    if shield_active:
                        # Shield protects from bad objects
                        if lose_sound:
                            lose_sound.play()
                        particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (0, 255, 255), 25))
                        objects_to_remove.append(obj)
                        # Remove shield after use
                        shield_active = False
                        if "shield" in powerup_timers:
                            del powerup_timers["shield"]
                    else:
                        # Game over
                        if lose_sound:
                            lose_sound.play()
                        particles.extend(create_particles(obj.rect.centerx, obj.rect.centery, (255, 0, 0), 30))
                        if score > high_score:
                            save_high_score(score)
                        game_over_screen(score, max_combo)
                        return

            # Remove object if it goes off screen
            if obj.rect.y > SCREEN_HEIGHT:
                if obj.obj_type == "fan":
                    combo = 0  # Reset combo if fan is missed
                objects_to_remove.append(obj)

        # Cleanup
        for obj in objects_to_remove:
            if obj in falling_objects:
                falling_objects.remove(obj)

        # 7. Update particles
        particles = [p for p in particles if p.life > 0]
        for particle in particles:
            particle.update()

        # 8. Draw everything
        # Draw falling objects
        for obj in falling_objects:
            obj.draw(screen)

        # Draw particles
        for particle in particles:
            particle.draw(screen)

        # Draw Zara with shield effect
        if shield_active:
            # Draw shield glow
            shield_surface = pygame.Surface((ZARA_WIDTH + 20, ZARA_HEIGHT + 20), pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surface, (0, 255, 255, 100), (0, 0, ZARA_WIDTH + 20, ZARA_HEIGHT + 20))
            screen.blit(shield_surface, (player_x - 10, player_y - 10))
        
        screen.blit(zara_img, (player_x, player_y))

        # 9. Draw UI
        # Score
        score_text = small_font.render(f"Score: {score}", True, (0, 0, 0))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 10))

        # High score
        high_score_text = small_font.render(f"High Score: {max(score, high_score)}", True, (0, 0, 0))
        screen.blit(high_score_text, (10, 10))

        # Combo
        if combo > 1:
            combo_text = small_font.render(f"Combo: {combo}x", True, (255, 0, 0))
            screen.blit(combo_text, (SCREEN_WIDTH - combo_text.get_width() - 10, 10))

        # Power-up indicators
        y_offset = 40
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

def start_screen():
    screen.fill((200,220,255))

    title_text = font.render("Only-Fanz V2", True, (0,0,0))
    subtitle_text = small_font.render("by Zara Dar", True, (0,0,0))
    play_text = small_font.render("Press [SPACE] to Play", True, (0,0,0))
    high_score = load_high_score()
    high_score_text = small_font.render(f"High Score: {high_score}", True, (0,0,0))
    
    # Instructions
    instructions = [
        "Catch fans for points!",
        "Avoid AC and heaters!",
        "Collect power-ups for special abilities:",
        "Cyan: Shield protection",
        "Yellow: Slow motion",
        "Magenta: Double points",
        "Green: Magnet for fans"
    ]

    screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, SCREEN_HEIGHT//2 - 120))
    screen.blit(subtitle_text, (SCREEN_WIDTH//2 - subtitle_text.get_width()//2, SCREEN_HEIGHT//2 - 90))
    screen.blit(play_text, (SCREEN_WIDTH//2 - play_text.get_width()//2, SCREEN_HEIGHT//2 - 60))
    screen.blit(high_score_text, (SCREEN_WIDTH//2 - high_score_text.get_width()//2, SCREEN_HEIGHT//2 - 30))

    # Draw instructions
    for i, instruction in enumerate(instructions):
        inst_text = tiny_font.render(instruction, True, (0,0,0))
        screen.blit(inst_text, (SCREEN_WIDTH//2 - inst_text.get_width()//2, SCREEN_HEIGHT//2 + 20 + i * 20))

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
