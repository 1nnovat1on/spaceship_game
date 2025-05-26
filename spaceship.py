import pygame
import math
import random

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (100, 100, 100)
GREEN = (0, 255, 0) # Cockpit color
BLUE_ISH = (180, 180, 255) # Alternative star color
REDDISH_PLANET = (200, 80, 80)
BLUEISH_PLANET = (80, 80, 200)
GREENISH_PLANET = (80, 200, 80)
LASER_COLOR = (255, 255, 0) # Yellow
PARTICLE_COLORS = [(255, 100, 0), (255, 165, 0), (255, 69, 0)] # Orange/Red Tones

# Starfield properties
NUM_STARS = 250 
FAR_Z = 500  
NEAR_Z_CLIP = 0.1 
FOV_SCALE = 300  
STAR_BASE_SIZE = 60 
MAX_STAR_DRAW_SIZE = 8 

# Player movement properties
BASE_SPEED_Z = 150  
BASE_ROTATION_SPEED_YAW = 1.8  
BASE_ROTATION_SPEED_PITCH = 1.5 

# Cockpit line thickness
COCKPIT_LINE_THICKNESS = 3

# Laser properties
LASER_SPEED = 400 # Units per second
LASER_LIFESPAN = 3.0 # seconds
LASER_RADIUS = 2 # For collision and drawing

# Particle properties
PARTICLE_LIFESPAN = 1.0 # seconds
PARTICLE_SPEED_MIN = 50
PARTICLE_SPEED_MAX = 150
NUM_PARTICLES_ON_EXPLOSION = 20
PARTICLE_RADIUS = 1

# --- Helper Functions ---
def random_vector(min_mag, max_mag):
    """Generates a random 3D vector with magnitude between min_mag and max_mag."""
    phi = random.uniform(0, math.pi * 2)
    costheta = random.uniform(-1, 1)
    theta = math.acos(costheta)
    mag = random.uniform(min_mag, max_mag)

    x = mag * math.sin(theta) * math.cos(phi)
    y = mag * math.sin(theta) * math.sin(phi)
    z = mag * math.cos(theta)
    return x, y, z

# --- Classes ---
class SpaceObject: 
    def __init__(self, x, y, z, color):
        self.x = x  # Relative to player's conceptual origin if not a projectile
        self.y = y
        self.z = z
        self.color = color
        self.screen_x = 0
        self.screen_y = 0
        self.is_active = True # All objects are active by default

    def project(self):
        raise NotImplementedError("Subclasses must implement this method")

    def draw(self, surface):
        raise NotImplementedError("Subclasses must implement this method")

    def update_view_transform(self, player_dz_dt, player_yaw_dt, player_pitch_dt):
        """Updates the object's 3D position based on player's movement and rotation."""
        # Translate along Z-axis (player's forward/backward movement affects object's relative Z)
        self.z -= player_dz_dt

        # --- Rotations due to player view change ---
        x_current = self.x
        y_current = self.y
        z_current = self.z # Use the z that was just updated by player thrust

        # Apply Yaw rotation (around player's Y-axis)
        if player_yaw_dt != 0:
            cos_yaw = math.cos(player_yaw_dt)
            sin_yaw = math.sin(player_yaw_dt)
            
            x_after_yaw = x_current * cos_yaw - z_current * sin_yaw
            z_after_yaw = x_current * sin_yaw + z_current * cos_yaw
            
            x_current = x_after_yaw
            z_current = z_after_yaw 

        # Apply Pitch rotation (around player's X-axis)
        if player_pitch_dt != 0:
            cos_pitch = math.cos(player_pitch_dt)
            sin_pitch = math.sin(player_pitch_dt)

            y_after_pitch = y_current * cos_pitch + z_current * sin_pitch 
            z_after_pitch = -y_current * sin_pitch + z_current * cos_pitch
            
            y_current = y_after_pitch
            z_current = z_after_pitch 

        # Assign final transformed coordinates back to the object
        self.x = x_current
        self.y = y_current
        self.z = z_current

    def update(self, dt, player_dz_dt, player_yaw_dt, player_pitch_dt):
        """General update method, to be called for all space objects."""
        self.update_view_transform(player_dz_dt, player_yaw_dt, player_pitch_dt)


class Star(SpaceObject):
    def __init__(self):
        temp_z = random.uniform(NEAR_Z_CLIP + 1, FAR_Z)
        max_spread_factor = 1.5 
        temp_x = random.uniform(-temp_z * max_spread_factor, temp_z * max_spread_factor)
        temp_y = random.uniform(-temp_z * max_spread_factor * (SCREEN_HEIGHT/SCREEN_WIDTH), 
                                 temp_z * max_spread_factor * (SCREEN_HEIGHT/SCREEN_WIDTH))
        
        if random.random() < 0.7: color = WHITE
        elif random.random() < 0.9: color = GREY
        else: color = BLUE_ISH
        super().__init__(temp_x, temp_y, temp_z, color)
        self.size = 0 

    def reset(self, initial_z=None):
        self.z = initial_z if initial_z is not None else random.uniform(NEAR_Z_CLIP + 1, FAR_Z)
        max_spread_factor = 1.5 
        self.x = random.uniform(-self.z * max_spread_factor, self.z * max_spread_factor)
        self.y = random.uniform(-self.z * max_spread_factor * (SCREEN_HEIGHT/SCREEN_WIDTH), 
                                 self.z * max_spread_factor * (SCREEN_HEIGHT/SCREEN_WIDTH))
        if random.random() < 0.7: self.color = WHITE
        elif random.random() < 0.9: self.color = GREY
        else: self.color = BLUE_ISH

    def project(self):
        if self.z <= NEAR_Z_CLIP: return False 
        self.screen_x = SCREEN_WIDTH / 2 + (self.x / self.z) * FOV_SCALE
        self.screen_y = SCREEN_HEIGHT / 2 + (self.y / self.z) * FOV_SCALE
        self.size = max(1, min(MAX_STAR_DRAW_SIZE, int(STAR_BASE_SIZE / self.z)))
        if not (0 <= self.screen_x <= SCREEN_WIDTH and 0 <= self.screen_y <= SCREEN_HEIGHT):
            return False 
        return True 

    def draw(self, surface):
        if self.project():
            pygame.draw.circle(surface, self.color, 
                               (int(self.screen_x), int(self.screen_y)), 
                               int(self.size))

    def update(self, dt, player_dz_dt, player_yaw_dt, player_pitch_dt, current_player_speed_z):
        """Star-specific update including reset logic."""
        super().update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
        if self.z <= NEAR_Z_CLIP : 
            self.reset(initial_z=FAR_Z) 
        elif self.z > FAR_Z * 1.5 and current_player_speed_z < 0 : 
             self.reset(initial_z=NEAR_Z_CLIP + 1)
        elif self.z > FAR_Z * 2: 
            self.reset(initial_z=FAR_Z)


class Planet(SpaceObject):
    def __init__(self, x, y, z, color, world_radius):
        super().__init__(x, y, z, color)
        self.world_radius = world_radius 
        self.screen_radius = 0 

    def project(self):
        if self.z <= NEAR_Z_CLIP: return False
        self.screen_x = SCREEN_WIDTH / 2 + (self.x / self.z) * FOV_SCALE
        self.screen_y = SCREEN_HEIGHT / 2 + (self.y / self.z) * FOV_SCALE
        self.screen_radius = max(1, int((self.world_radius / self.z) * FOV_SCALE ))
        
        if not (self.screen_x + self.screen_radius > 0 and \
                self.screen_x - self.screen_radius < SCREEN_WIDTH and \
                self.screen_y + self.screen_radius > 0 and \
                self.screen_y - self.screen_radius < SCREEN_HEIGHT):
            if self.z > FAR_Z * 3 and self.screen_radius < 2 : return False
            if abs(self.screen_x - SCREEN_WIDTH/2) > SCREEN_WIDTH + self.screen_radius or \
               abs(self.screen_y - SCREEN_HEIGHT/2) > SCREEN_HEIGHT + self.screen_radius :
                if self.z > NEAR_Z_CLIP * 2 : return False
        return True

    def draw(self, surface):
        if self.project():
            draw_radius = min(self.screen_radius, max(SCREEN_WIDTH, SCREEN_HEIGHT)) 
            pygame.draw.circle(surface, self.color,
                               (int(self.screen_x), int(self.screen_y)),
                               int(draw_radius))

class Projectile(SpaceObject):
    def __init__(self, x, y, z, vel_x, vel_y, vel_z, lifespan, color, radius):
        super().__init__(x, y, z, color)
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.vel_z = vel_z
        self.lifespan = lifespan
        self.world_radius = radius # Using world_radius for consistency in collision
        self.screen_radius = 0

    def move_self(self, dt):
        """Projectile moves itself in its own (world) direction."""
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        self.z += self.vel_z * dt
        self.lifespan -= dt
        if self.lifespan <= 0:
            self.is_active = False
        # Deactivate if too far (simple Z check for now)
        if abs(self.z) > FAR_Z * 4: # Lasers can go quite far
            self.is_active = False


    def update(self, dt, player_dz_dt, player_yaw_dt, player_pitch_dt):
        """Projectile update: first moves itself, then applies player view transform."""
        if not self.is_active:
            return
        self.move_self(dt)
        super().update_view_transform(player_dz_dt, player_yaw_dt, player_pitch_dt) # Apply view transform to new pos

    def project(self): # Generic projection for small projectiles
        if not self.is_active or self.z <= NEAR_Z_CLIP:
            return False
        self.screen_x = SCREEN_WIDTH / 2 + (self.x / self.z) * FOV_SCALE
        self.screen_y = SCREEN_HEIGHT / 2 + (self.y / self.z) * FOV_SCALE
        self.screen_radius = max(1, int((self.world_radius / self.z) * FOV_SCALE))
        
        if not (self.screen_x + self.screen_radius > 0 and \
                self.screen_x - self.screen_radius < SCREEN_WIDTH and \
                self.screen_y + self.screen_radius > 0 and \
                self.screen_y - self.screen_radius < SCREEN_HEIGHT):
            return False
        return True

    def draw(self, surface):
        if self.project():
            # Ensure radius is at least 1 for visibility
            draw_radius = max(1, self.screen_radius)
            pygame.draw.circle(surface, self.color,
                               (int(self.screen_x), int(self.screen_y)),
                               int(draw_radius))


def draw_cockpit(surface):
    pygame.draw.line(surface, GREEN, (0, SCREEN_HEIGHT * 0.85), (SCREEN_WIDTH, SCREEN_HEIGHT * 0.85), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.1, SCREEN_HEIGHT), (SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.75), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.9, SCREEN_HEIGHT), (SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.75), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.1), (SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.1), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.1), (SCREEN_WIDTH * 0.35, SCREEN_HEIGHT * 0.2), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.1), (SCREEN_WIDTH * 0.65, SCREEN_HEIGHT * 0.2), COCKPIT_LINE_THICKNESS)
    center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    reticle_size = 10
    pygame.draw.line(surface, GREEN, (center_x - reticle_size, center_y), (center_x + reticle_size, center_y), 1)
    pygame.draw.line(surface, GREEN, (center_x, center_y - reticle_size), (center_x, center_y + reticle_size), 1)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Wireframe Spaceship - Advanced")
    clock = pygame.time.Clock()

    # --- Game State Variables ---
    game_time_seconds = 0
    last_second_tick = pygame.time.get_ticks()
    time_font = pygame.font.Font(None, 36) # Font for timer

    stars = [Star() for _ in range(NUM_STARS)]
    planets = [
        Planet(x=0, y=0, z=1000, color=REDDISH_PLANET, world_radius=100),
        Planet(x=1200, y=300, z=1800, color=BLUEISH_PLANET, world_radius=150),
        Planet(x=-800, y=-400, z=1200, color=GREENISH_PLANET, world_radius=80),
        Planet(x=200, y=1000, z=2500, color=GREY, world_radius=120) 
    ]
    
    # Combined list for rendering and general updates. Projectiles added here.
    space_objects = stars + planets 
    
    active_lasers = [] 
    # active_particles list was unused, removed. Particles are managed within space_objects.

    current_speed_z = 0
    current_rotation_yaw_speed = 0 
    current_rotation_pitch_speed = 0 

    player_total_yaw_angle = 0.0
    player_total_pitch_angle = 0.0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  
        if dt == 0: dt = 1/FPS 

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    # Fire Laser
                    lx, ly, lz = 0, 0, -1 

                    cos_p_inv = math.cos(-player_total_pitch_angle)
                    sin_p_inv = math.sin(-player_total_pitch_angle)
                    lx1, ly1, lz1 = lx, ly * cos_p_inv - lz * sin_p_inv, ly * sin_p_inv + lz * cos_p_inv
                    
                    cos_y_inv = math.cos(-player_total_yaw_angle)
                    sin_y_inv = math.sin(-player_total_yaw_angle)
                    world_dx = lx1 * cos_y_inv + lz1 * sin_y_inv
                    world_dy = ly1 
                    world_dz = -lx1 * sin_y_inv + lz1 * cos_y_inv
                    
                    norm = math.sqrt(world_dx**2 + world_dy**2 + world_dz**2)
                    if norm > 0:
                        world_dx = world_dx / norm * LASER_SPEED
                        world_dy = world_dy / norm * LASER_SPEED
                        world_dz = world_dz / norm * LASER_SPEED

                    new_laser = Projectile(0, 0, NEAR_Z_CLIP, world_dx, world_dy, world_dz, LASER_LIFESPAN, LASER_COLOR, LASER_RADIUS)
                    active_lasers.append(new_laser)
                    space_objects.append(new_laser)


        # --- Input Handling ---
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_UP]: current_speed_z = BASE_SPEED_Z
        elif keys[pygame.K_DOWN]: current_speed_z = -BASE_SPEED_Z / 2 
        else: current_speed_z = 0
            
        if keys[pygame.K_LEFT]: current_rotation_yaw_speed = -BASE_ROTATION_SPEED_YAW 
        elif keys[pygame.K_RIGHT]: current_rotation_yaw_speed = BASE_ROTATION_SPEED_YAW
        else: current_rotation_yaw_speed = 0
        
        if keys[pygame.K_w]: current_rotation_pitch_speed = BASE_ROTATION_SPEED_PITCH 
        elif keys[pygame.K_s]: current_rotation_pitch_speed = -BASE_ROTATION_SPEED_PITCH
        else: current_rotation_pitch_speed = 0

        # --- Update Game Logic ---
        
        player_total_yaw_angle += current_rotation_yaw_speed * dt
        player_total_pitch_angle += current_rotation_pitch_speed * dt
        player_total_pitch_angle = max(-math.pi/2 * 0.95, min(math.pi/2 * 0.95, player_total_pitch_angle)) 


        player_dz_dt = current_speed_z * dt
        player_yaw_dt = current_rotation_yaw_speed * dt 
        player_pitch_dt = current_rotation_pitch_speed * dt 


        new_space_objects_list = []
        for obj in space_objects:
            if not obj.is_active: 
                continue

            if isinstance(obj, Star):
                 obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt, current_speed_z)
            elif isinstance(obj, Projectile): 
                obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
            else: # Planets
                obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
            
            if obj.is_active: 
                new_space_objects_list.append(obj)
        space_objects = new_space_objects_list
        active_lasers = [l for l in active_lasers if l.is_active] 

        lasers_to_remove_after_collision = []
        for laser in active_lasers:
            if not laser.is_active: continue
            for planet in planets:
                dist_sq = (laser.x - planet.x)**2 + (laser.y - planet.y)**2 + (laser.z - planet.z)**2
                if dist_sq < (planet.world_radius + laser.world_radius)**2:
                    laser.is_active = False 
                    lasers_to_remove_after_collision.append(laser)
                    
                    impact_x, impact_y, impact_z = laser.x, laser.y, laser.z 
                    for _ in range(NUM_PARTICLES_ON_EXPLOSION):
                        p_vx, p_vy, p_vz = random_vector(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
                        new_particle = Projectile(impact_x, impact_y, impact_z, 
                                                  p_vx, p_vy, p_vz, 
                                                  PARTICLE_LIFESPAN, random.choice(PARTICLE_COLORS), PARTICLE_RADIUS)
                        space_objects.append(new_particle) 
                    break 
            if not laser.is_active: 
                break
        
        if lasers_to_remove_after_collision:
            space_objects = [obj for obj in space_objects if obj not in lasers_to_remove_after_collision]
            active_lasers = [l for l in active_lasers if l not in lasers_to_remove_after_collision]

        # Update time counter
        current_ticks = pygame.time.get_ticks()
        if current_ticks - last_second_tick >= 1000:
            game_time_seconds += 1
            if game_time_seconds > 999: # Reset if it exceeds 999
                game_time_seconds = 0
            last_second_tick = current_ticks
        
        space_objects.sort(key=lambda obj: obj.z, reverse=True)

        # --- Drawing ---
        screen.fill(BLACK)

        for obj in space_objects:
            if obj.is_active: 
                obj.draw(screen) 
        
        draw_cockpit(screen)

        time_surface = time_font.render(f"Time: {game_time_seconds}", True, WHITE)
        screen.blit(time_surface, (10, 10))

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
