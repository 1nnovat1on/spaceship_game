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
NUM_PARTICLES_ON_EXPLOSION_PLANET = 50 # Added this during planet health task, ensure it's kept if it was separate
PARTICLE_RADIUS = 1

# Enemy properties
ENEMY_SPAWN_INTERVAL = 20.0 # seconds
MAX_ENEMIES = 3
ENEMY_HEALTH = 50
ENEMY_SPEED = 35 # Units per second
ENEMY_FIRE_RATE = 3.0 # seconds between shots
ENEMY_LASER_COLOR = (255, 50, 50) # Bright Red for enemy lasers
ENEMY_WORLD_RADIUS = 15 
ENEMY_COLOR = (200, 0, 0) # Dark Red for enemy ship body

# Player properties
PLAYER_HITBOX_RADIUS = 10 # For collision with enemy lasers
PLAYER_MAX_HEALTH = 100

# Universe properties
UNIVERSE_LIFESPAN_SECONDS = 120 # e.g., 2 minutes for testing

# Comet Properties
COMET_COLOR = (200, 200, 255) # Light blueish-white
COMET_SPAWN_INTERVAL = 15.0 # seconds
MAX_COMETS = 2
COMET_TAIL_LENGTH = 30 # Number of segments
COMET_HEAD_RADIUS = 8
COMET_SPEED_MIN = 100
COMET_SPEED_MAX = 200

# Points System
POINTS_PER_ENEMY_DESTROYED = 100
POINTS_PER_PLANET_DESTROYED = 500
POINTS_PER_DISTANCE_UNIT = 0.01 # 1 point per 100 z-units forward movement

# Black Hole Properties
BLACK_HOLE_COLOR = BLACK # Defined in Colors
BLACK_HOLE_SPAWN_INTERVAL = 45.0 # seconds, make them somewhat rare
MAX_BLACK_HOLES = 1 # Start with one for testing, can increase
BLACK_HOLE_RADIUS_MIN = 20
BLACK_HOLE_RADIUS_MAX = 40
GRAVITY_RADIUS_FACTOR = 5.0 # Effective gravity radius = world_radius * this factor
EVENT_HORIZON_FACTOR = 0.4 # Event horizon radius = world_radius * this factor
GRAVITY_STRENGTH_MIN = 5000 # Arbitrary units, adjust based on testing
GRAVITY_STRENGTH_MAX = 15000
MAX_GRAVITY_FORCE_GENERAL = 100.0 # Max pull force on general objects per frame
MAX_GRAVITY_FORCE_ON_PLAYER = 0.3 # Max influence on player's movement params per sec
PLAYER_TURN_RESPONSE_TO_GRAVITY = 0.05 # How much player view turns towards black hole

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
    def __init__(self, x, y, z, color, world_radius, health=100): # Added health, default 100
        super().__init__(x, y, z, color)
        self.world_radius = world_radius
        self.health = health # Initialize health
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
    def __init__(self, x, y, z, vel_x, vel_y, vel_z, lifespan, color, radius, owner="player"): # Added owner
        super().__init__(x, y, z, color)
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.vel_z = vel_z
        self.lifespan = lifespan
        self.world_radius = radius 
        self.owner = owner # Store the owner ("player", "enemy", "neutral_explosion")
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

class EnemyShip(SpaceObject):
    def __init__(self, x, y, z, color, world_radius, speed, health, fire_rate, current_game_time):
        super().__init__(x, y, z, color)
        self.world_radius = world_radius
        self.speed = speed
        self.health = health
        self.fire_rate = fire_rate
        # Initialize last_fire_time to current_game_time to prevent immediate firing
        # Add a small random delay to stagger initial firing if multiple enemies spawn together
        self.last_fire_time = current_game_time + random.uniform(0, fire_rate) 
        self.screen_radius = 0 

    def project(self): # Can reuse/adapt Planet's projection
        if self.z <= NEAR_Z_CLIP: return False
        self.screen_x = SCREEN_WIDTH / 2 + (self.x / self.z) * FOV_SCALE
        self.screen_y = SCREEN_HEIGHT / 2 + (self.y / self.z) * FOV_SCALE
        self.screen_radius = max(1, int((self.world_radius / self.z) * FOV_SCALE ))
        
        # Basic culling if too far off-screen
        if not (self.screen_x + self.screen_radius > 0 and \
                self.screen_x - self.screen_radius < SCREEN_WIDTH and \
                self.screen_y + self.screen_radius > 0 and \
                self.screen_y - self.screen_radius < SCREEN_HEIGHT):
            # More aggressive culling if far away and way off screen
            if self.z > FAR_Z * 1.2 and (abs(self.screen_x - SCREEN_WIDTH/2) > SCREEN_WIDTH/2 + self.screen_radius * 5):
                 return False
        return True

    def draw(self, surface):
        if self.project():
            pygame.draw.circle(surface, self.color,
                               (int(self.screen_x), int(self.screen_y)),
                               int(self.screen_radius))
            # Simple "cockpit" highlight
            highlight_color = (min(255,self.color[0]+60), min(255,self.color[1]+60), min(255,self.color[2]+60))
            pygame.draw.circle(surface, highlight_color, 
                               (int(self.screen_x), int(self.screen_y)), 
                               int(self.screen_radius * 0.5))


    def update_ai(self, dt, player_conceptual_x, player_conceptual_y, player_conceptual_z, 
                  active_projectiles_list, current_game_time, mixer_initialized, enemy_laser_sound):
        # AI Movement: Target a point slightly in front of the player and attempt to match Z.
        # player_conceptual_x,y,z are (0,0,0) as player is origin in their own view space.
        target_z_distance = 100 + (self.world_radius * 2) # Try to maintain this Z distance from player
        
        # Vector from enemy to player's conceptual position + offset
        dx = player_conceptual_x - self.x
        dy = player_conceptual_y - self.y 
        dz = (player_conceptual_z + target_z_distance) - self.z
        
        distance_to_target_point = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance_to_target_point > self.speed * dt * 0.5 : # Move if not too close
            self.x += (dx / distance_to_target_point) * self.speed * dt
            self.y += (dy / distance_to_target_point) * self.speed * dt
            self.z += (dz / distance_to_target_point) * self.speed * dt
        
        # Keep enemy within reasonable Z bounds
        self.z = max(NEAR_Z_CLIP + self.world_radius + 5, min(self.z, FAR_Z * 1.25))

        # Shooting Logic
        if current_game_time - self.last_fire_time > self.fire_rate:
            # Vector from enemy to player (player is at (0,0,0) conceptually for enemy AI)
            fire_dir_x = player_conceptual_x - self.x
            fire_dir_y = player_conceptual_y - self.y
            fire_dir_z = player_conceptual_z - self.z 

            norm = math.sqrt(fire_dir_x**2 + fire_dir_y**2 + fire_dir_z**2)
            if norm > 0: # Avoid division by zero
                vel_x = (fire_dir_x / norm) * LASER_SPEED
                vel_y = (fire_dir_y / norm) * LASER_SPEED
                vel_z = (fire_dir_z / norm) * LASER_SPEED

                # Create enemy laser, add to main space_objects list
                new_enemy_laser = Projectile(self.x, self.y, self.z, 
                                             vel_x, vel_y, vel_z, 
                                             LASER_LIFESPAN, ENEMY_LASER_COLOR, LASER_RADIUS, owner="enemy")
                active_projectiles_list.append(new_enemy_laser) 
                self.last_fire_time = current_game_time

                if mixer_initialized and enemy_laser_sound: # Check if sound object exists
                    enemy_laser_sound.play()

    def update(self, dt, player_dz_dt, player_yaw_dt, player_pitch_dt, 
               player_conceptual_x, player_conceptual_y, player_conceptual_z, 
               active_projectiles_list, current_game_time, mixer_initialized, enemy_laser_sound):
        if not self.is_active:
            return
        
        self.update_ai(dt, player_conceptual_x, player_conceptual_y, player_conceptual_z, 
                       active_projectiles_list, current_game_time, mixer_initialized, enemy_laser_sound)
        
        # After AI logic (which moves the ship in its conceptual space relative to player at origin),
        # apply player's view transform to get its final screen position.
        super().update_view_transform(player_dz_dt, player_yaw_dt, player_pitch_dt)


def draw_cockpit(surface):
    pygame.draw.line(surface, GREEN, (0, SCREEN_HEIGHT * 0.85), (SCREEN_WIDTH, SCREEN_HEIGHT * 0.85), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.1, SCREEN_HEIGHT), (SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.75), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.9, SCREEN_HEIGHT), (SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.75), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.1), (SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.1), COCKPIT_LINE_THICKNESS)

class Comet(SpaceObject):
    def __init__(self, x, y, z, world_radius, color, velocity_vector, tail_length=20,
                 fov_scale=FOV_SCALE, screen_w=SCREEN_WIDTH, screen_h=SCREEN_HEIGHT, near_z=NEAR_Z_CLIP):
        super().__init__(x, y, z, color)
        self.world_radius = world_radius
        self.velocity = velocity_vector # (vx, vy, vz)
        self.tail_length = tail_length
        # Stores original world coordinates of tail points before view transformation
        self.tail_world_coords = [] 
        # Stores view-transformed coordinates of tail points for drawing this frame
        self.view_transformed_tail_for_drawing = [] 

        # Store projection parameters (alternatively, access globals if defined consistently)
        self.fov_scale = fov_scale
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.near_z = near_z
        self.screen_head_radius = 0 # For the projected head radius

    def move_self(self, dt):
        # Update head position in world space
        self.x += self.velocity[0] * dt
        self.y += self.velocity[1] * dt
        self.z += self.velocity[2] * dt

        # Add current head position to the list of world tail coordinates
        self.tail_world_coords.append({'x': self.x, 'y': self.y, 'z': self.z, 'radius': self.world_radius}) # Store original radius too

        # Maintain tail length
        while len(self.tail_world_coords) > self.tail_length:
            self.tail_world_coords.pop(0)

        # Deactivation logic (simple version)
        # Check if comet is way off screen in any direction relative to its current Z
        # This is a rough check; more precise culling would involve projecting bounds
        current_max_spread = abs(self.z) * 2 # Example: if at z=500, allow x/y up to 1000
        if abs(self.x) > current_max_spread or \
           abs(self.y) > current_max_spread * (self.screen_h / self.screen_w) or \
           self.z < -FAR_Z or self.z > FAR_Z * 3: # Check Z bounds too
            # A more robust check would be if it's far behind player or very far away and moving further
            if self.z < self.near_z - 200 or self.z > FAR_Z * 4: # If significantly behind or extremely far
                 self.is_active = False


    def _project_single_point(self, x, y, z, base_world_radius):
        """Helper to project a single 3D point (already view-relative) to 2D screen space."""
        if z <= self.near_z:
            return None
        
        screen_x = self.screen_w / 2 + (x / z) * self.fov_scale
        screen_y = self.screen_h / 2 + (y / z) * self.fov_scale # Assumes Pygame Y-down, world Y-up
        
        # Scale radius based on distance
        screen_radius = max(1, int((base_world_radius / z) * self.fov_scale))
        
        # Basic culling for the point itself (not its radius extent)
        # if not (0 <= screen_x <= self.screen_w and 0 <= screen_y <= self.screen_h):
        #     return None # Point itself is off-screen
            
        return screen_x, screen_y, screen_radius

    def update(self, dt, player_dz_dt, player_yaw_dt, player_pitch_dt):
        if not self.is_active:
            return

        self.move_self(dt) # Update head world pos, manage tail_world_coords

        # Transform head to view-relative world coordinates
        # This modifies self.x, self.y, self.z directly
        super().update_view_transform(player_dz_dt, player_yaw_dt, player_pitch_dt)
        
        # Now, transform all world tail coordinates to view-relative for this frame's drawing
        self.view_transformed_tail_for_drawing = []
        for world_point in self.tail_world_coords:
            tx, ty, tz = world_point['x'], world_point['y'], world_point['z']
            
            # 1. Apply player's translation (opposite of player's Z movement)
            tz -= player_dz_dt
            
            # 2. Apply player's yaw rotation (around Y-axis)
            if player_yaw_dt != 0:
                cos_yaw = math.cos(player_yaw_dt)
                sin_yaw = math.sin(player_yaw_dt)
                temp_tx_yaw = tx * cos_yaw - tz * sin_yaw
                tz_after_yaw = tx * sin_yaw + tz * cos_yaw
                tx, tz = temp_tx_yaw, tz_after_yaw
            
            # 3. Apply player's pitch rotation (around X-axis)
            if player_pitch_dt != 0:
                cos_pitch = math.cos(player_pitch_dt)
                sin_pitch = math.sin(player_pitch_dt)
                temp_ty_pitch = ty * cos_pitch + tz * sin_pitch
                tz_after_pitch = -ty * sin_pitch + tz * cos_pitch
                ty, tz = temp_ty_pitch, tz_after_pitch
            
            self.view_transformed_tail_for_drawing.append({'x': tx, 'y': ty, 'z': tz, 'radius': world_point['radius']})

    def draw(self, surface):
        # Project and draw the head
        # The head's self.x, self.y, self.z are already view-transformed by its update method
        head_projection = self._project_single_point(self.x, self.y, self.z, self.world_radius)
        
        if head_projection:
            sx_head, sy_head, sr_head = head_projection
            self.screen_head_radius = sr_head # Store for potential use
            pygame.draw.circle(surface, self.color, (int(sx_head), int(sy_head)), int(sr_head))

            # Draw the tail (already view-transformed)
            num_tail_points = len(self.view_transformed_tail_for_drawing)
            for i, view_point in enumerate(self.view_transformed_tail_for_drawing):
                tail_projection = self._project_single_point(view_point['x'], view_point['y'], view_point['z'], view_point['radius'])
                if tail_projection:
                    sx_tail, sy_tail, sr_tail_base = tail_projection
                    
                    # Make tail segments smaller and dimmer with age (further down the list)
                    age_factor = (i + 1) / num_tail_points # Ranges from ~0 (oldest) to 1 (newest, near head)
                    current_radius = max(1, int(sr_tail_base * age_factor * 0.7)) # Taper tail
                    
                    # Fade color/alpha (simple version: reduce brightness)
                    alpha = int(100 + 155 * age_factor) # Fade from semi-transparent to fully opaque
                    tail_color = (max(0, self.color[0] - int(70 * (1-age_factor))),
                                  max(0, self.color[1] - int(70 * (1-age_factor))),
                                  max(0, self.color[2] - int(40 * (1-age_factor))))
                    
                    # Pygame doesn't directly support alpha per draw on main surface easily.
                    # For a simple effect, we can just change color. For true alpha, need per-pixel or separate surfaces.
                    # Here, we just use the modified color.
                    pygame.draw.circle(surface, tail_color, (int(sx_tail), int(sy_tail)), current_radius)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.1), (SCREEN_WIDTH * 0.35, SCREEN_HEIGHT * 0.2), COCKPIT_LINE_THICKNESS)
    pygame.draw.line(surface, GREEN, (SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.1), (SCREEN_WIDTH * 0.65, SCREEN_HEIGHT * 0.2), COCKPIT_LINE_THICKNESS)
    center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    reticle_size = 10
    pygame.draw.line(surface, GREEN, (center_x - reticle_size, center_y), (center_x + reticle_size, center_y), 1)
    pygame.draw.line(surface, GREEN, (center_x, center_y - reticle_size), (center_x, center_y + reticle_size), 1)

class BlackHole(SpaceObject):
    def __init__(self, x, y, z, world_radius, color, gravity_radius, gravity_strength, event_horizon_radius):
        super().__init__(x, y, z, color)
        self.world_radius = world_radius # Visual radius
        self.gravity_radius = gravity_radius # Range of gravitational pull
        self.gravity_strength = gravity_strength # Strength of the pull
        self.event_horizon_radius = event_horizon_radius # "Point of no return"
        self.screen_radius = 0 # For projection

    def project(self): # Similar to Planet/EnemyShip
        if self.z <= NEAR_Z_CLIP: return False
        self.screen_x = SCREEN_WIDTH / 2 + (self.x / self.z) * FOV_SCALE
        self.screen_y = SCREEN_HEIGHT / 2 + (self.y / self.z) * FOV_SCALE
        self.screen_radius = max(1, int((self.world_radius / self.z) * FOV_SCALE ))
        
        # Basic culling
        if not (self.screen_x + self.screen_radius * GRAVITY_RADIUS_FACTOR > 0 and \
                self.screen_x - self.screen_radius * GRAVITY_RADIUS_FACTOR < SCREEN_WIDTH and \
                self.screen_y + self.screen_radius * GRAVITY_RADIUS_FACTOR > 0 and \
                self.screen_y - self.screen_radius * GRAVITY_RADIUS_FACTOR < SCREEN_HEIGHT):
            if self.z > FAR_Z * 1.1 : return False 
        return True

    def draw(self, surface):
        if self.project():
            # Draw the event horizon (visual representation of the black hole itself)
            pygame.draw.circle(surface, self.color, # Should be BLACK
                               (int(self.screen_x), int(self.screen_y)),
                               int(self.screen_radius))
            
            # Optional: Draw a faint outer circle for gravity radius for debugging/visual cue
            # This radius needs to be projected as well
            projected_gravity_radius_on_screen = max(1, int((self.gravity_radius / self.z) * FOV_SCALE))
            if projected_gravity_radius_on_screen > self.screen_radius:
                 # Create a very faint color for the gravity well, e.g., dark grey or purple
                gravity_well_color = (30, 30, 50) # Dark Purple/Blueish
                # This is a simplified way to draw; for true alpha blending, more complex surface handling is needed.
                # We can draw multiple faint circles or use a pre-rendered alpha image.
                # For now, a simple slightly larger, darker circle.
                temp_surface = pygame.Surface((projected_gravity_radius_on_screen*2, projected_gravity_radius_on_screen*2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surface, (*gravity_well_color, 50), 
                                   (projected_gravity_radius_on_screen, projected_gravity_radius_on_screen), 
                                   projected_gravity_radius_on_screen)
                surface.blit(temp_surface, (int(self.screen_x - projected_gravity_radius_on_screen), 
                                            int(self.screen_y - projected_gravity_radius_on_screen)))


    def update(self, dt, player_dz_dt, player_yaw_dt, player_pitch_dt):
        # Black holes are generally static in their own position unless explicitly moved by game logic
        # Their main interaction comes from apply_gravity, called from main loop
        # But they still need their view coordinates updated based on player movement
        super().update_view_transform(player_dz_dt, player_yaw_dt, player_pitch_dt)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Wireframe Spaceship - Advanced")
    clock = pygame.time.Clock()

    # --- Game State Variables ---
    game_time_seconds = 0 # For on-screen timer
    last_second_tick = pygame.time.get_ticks() # For on-screen timer
    time_font = pygame.font.Font(None, 36) 
    player_health_display_font = pygame.font.Font(None, 30) # Font for player health
    score_font = pygame.font.Font(None, 30) 

    player_health = PLAYER_MAX_HEALTH
    player_score = 0 
    # Use overall game time in seconds for timed logic like spawning
    # This is distinct from game_time_seconds which is just for display
    game_current_time_seconds_logic = pygame.time.get_ticks() / 1000.0 
    last_enemy_spawn_time = game_current_time_seconds_logic 
    last_comet_spawn_time = game_current_time_seconds_logic 
    last_black_hole_spawn_time = game_current_time_seconds_logic # For black holes

    stars = [Star() for _ in range(NUM_STARS)]
    # Assuming Planet class was previously modified to include health for planets
    # If not, this instantiation would need to be updated or Planet class modified here too.
    # For this task, we assume Planet is as it was after its own health implementation.
    _initial_planets = [
        Planet(x=0, y=0, z=1000, color=REDDISH_PLANET, world_radius=100, health=100), 
        Planet(x=1200, y=300, z=1800, color=BLUEISH_PLANET, world_radius=150, health=100),
        Planet(x=-800, y=-400, z=1200, color=GREENISH_PLANET, world_radius=80, health=100),
        Planet(x=200, y=1000, z=2500, color=GREY, world_radius=120, health=100) 
    ]
    
    space_objects = stars + _initial_planets 
    active_enemies = [] 
    active_comets = [] 
    active_black_holes = [] # List to manage active black holes

    # Player lasers and enemy lasers will be filtered from space_objects each frame.
    # No need for a persistent 'active_lasers' list for player's lasers.

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
                    # Fire Laser (direction was changed to +Z in a previous subtask)
                    lx, ly, lz = 0, 0, 1 # Should be +1 if forward is +Z in view space

                    # Apply inverse player rotation to get world direction
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
                        world_dx_norm = world_dx / norm * LASER_SPEED
                        world_dy_norm = world_dy / norm * LASER_SPEED
                        world_dz_norm = world_dz / norm * LASER_SPEED

                    # Create player laser with owner="player"
                    new_player_laser = Projectile(0, 0, NEAR_Z_CLIP, world_dx_norm, world_dy_norm, world_dz_norm, 
                                                  LASER_LIFESPAN, LASER_COLOR, LASER_RADIUS, owner="player")
                    space_objects.append(new_player_laser) # Add to main list
                    
                    # Play laser sound (assuming mixer_initialized and laser_fire_sound are available)
                    if 'mixer_initialized' in locals() and mixer_initialized and 'laser_fire_sound' in locals() and laser_fire_sound:
                        laser_fire_sound.play()


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

        # Award points for forward travel
        if current_speed_z > 0: # Player is moving forward
            # player_dz_dt is the distance travelled in Z this frame
            score_from_travel = POINTS_PER_DISTANCE_UNIT * player_dz_dt
            player_score += int(score_from_travel)


        new_space_objects_list = []
        for obj in space_objects:
            if not obj.is_active: 
                continue

            if isinstance(obj, Star):
                 obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt, current_speed_z)
            elif isinstance(obj, Projectile):
                obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
            elif isinstance(obj, EnemyShip):
                game_current_time_seconds_logic = pygame.time.get_ticks() / 1000.0
                # Player conceptual coordinates for AI are (0,0,0)
                _enemy_laser_sound = enemy_laser_sound if 'mixer_initialized' in locals() and mixer_initialized and 'enemy_laser_sound' in locals() else None
                obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt, 
                           player_conceptual_x=0, player_conceptual_y=0, player_conceptual_z=0, 
                           active_projectiles_list=space_objects, 
                           current_game_time=game_current_time_seconds_logic,
                           mixer_initialized=mixer_initialized if 'mixer_initialized' in locals() else False,
                           enemy_laser_sound=_enemy_laser_sound)
            elif isinstance(obj, BlackHole): # Update Black Hole position based on player movement
                 obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
            elif isinstance(obj, Comet):
                obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
            elif isinstance(obj, Planet): 
                obj.update(dt, player_dz_dt, player_yaw_dt, player_pitch_dt)
            
            if obj.is_active: 
                new_space_objects_list.append(obj)
        space_objects = new_space_objects_list 

        # Filter lasers by owner for collision checks
        # These are filtered every frame from the main space_objects list
        player_lasers_this_frame = [p for p in space_objects if isinstance(p, Projectile) and p.owner == "player" and p.is_active]
        enemy_lasers_this_frame = [p for p in space_objects if isinstance(p, Projectile) and p.owner == "enemy" and p.is_active]
        
        # --- Gravity Application and Black Hole Interactions ---
        player_acceleration_effect = [0.0, 0.0, 0.0] # x, y, z components for player pull
        temp_particles_to_add_from_bh = [] # Particles from objects consumed by BH

        for bh in active_black_holes:
            if not bh.is_active: continue

            # 1. Player interaction with Black Hole
            # Player is at (0,0,0) in view-relative space. bh.x,y,z are already view-relative.
            dx_player_to_bh = bh.x 
            dy_player_to_bh = bh.y
            dz_player_to_bh = bh.z
            dist_sq_player = dx_player_to_bh**2 + dy_player_to_bh**2 + dz_player_to_bh**2

            if dist_sq_player < bh.gravity_radius**2 :
                if dist_sq_player < bh.event_horizon_radius**2 and player_health > 0: # Only trigger once
                    player_health = 0 # Game Over
                    if _player_hit_sound: _player_hit_sound.play() # Or specific BH death sound
                    print("Player consumed by black hole!")
                    # Potentially set running = False here or handle game over state
                elif player_health > 0 : # Apply pull if player not already dead
                    norm_player = math.sqrt(dist_sq_player) if dist_sq_player > 0.001 else 1.0
                    pull_dir_x = dx_player_to_bh / norm_player
                    pull_dir_y = dy_player_to_bh / norm_player
                    pull_dir_z = dz_player_to_bh / norm_player
                    
                    # Force inversely proportional to distance squared (more realistic)
                    force_magnitude = bh.gravity_strength / (dist_sq_player + 1.0) # Add 1 to avoid extreme force at very close range
                    force_magnitude = min(force_magnitude, MAX_GRAVITY_FORCE_ON_PLAYER / dt if dt > 0 else MAX_GRAVITY_FORCE_ON_PLAYER) # Cap effective acceleration
                    
                    player_acceleration_effect[0] += pull_dir_x * force_magnitude
                    player_acceleration_effect[1] += pull_dir_y * force_magnitude
                    player_acceleration_effect[2] += pull_dir_z * force_magnitude

            # 2. Other objects (Enemies, Comets, Projectiles) vs Black Hole
            # Important: Iterate over a copy if objects might be removed or added during this loop
            # However, we are just marking them inactive or changing their properties.
            # New particles are added to a temporary list.
            for obj in space_objects:
                if obj is bh or not obj.is_active or obj is None: # Skip self, inactive, or None
                    continue
                # Ensure it's a movable object (has x,y,z and is not a Star for simplicity)
                if not (isinstance(obj, EnemyShip) or isinstance(obj, Comet) or isinstance(obj, Projectile)):
                    continue

                dx_obj_to_bh = bh.x - obj.x
                dy_obj_to_bh = bh.y - obj.y
                dz_obj_to_bh = bh.z - obj.z
                dist_sq_obj = dx_obj_to_bh**2 + dy_obj_to_bh**2 + dz_obj_to_bh**2

                if dist_sq_obj < bh.gravity_radius**2:
                    if dist_sq_obj < bh.event_horizon_radius**2:
                        obj.is_active = False # Consumed
                        # Particle effect for consumption
                        for _ in range(NUM_PARTICLES_ON_EXPLOSION // 3): # Fewer particles
                            p_vel = random_vector(PARTICLE_SPEED_MIN / 2, PARTICLE_SPEED_MAX / 2)
                            # Spawn particles moving towards black hole center
                            norm_to_bh = math.sqrt(dist_sq_obj) if dist_sq_obj > 0 else 1
                            p_vx = (dx_obj_to_bh / norm_to_bh) * PARTICLE_SPEED_MAX * 0.5
                            p_vy = (dy_obj_to_bh / norm_to_bh) * PARTICLE_SPEED_MAX * 0.5
                            p_vz = (dz_obj_to_bh / norm_to_bh) * PARTICLE_SPEED_MAX * 0.5
                            temp_particles_to_add_from_bh.append(
                                Projectile(obj.x, obj.y, obj.z, p_vx, p_vy, p_vz,
                                           PARTICLE_LIFESPAN * 0.5, random.choice(PARTICLE_COLORS), PARTICLE_RADIUS, owner="neutral_bh_effect")
                            )
                        if 'mixer_initialized' in locals() and mixer_initialized:
                            if 'black_hole_sound' in locals() and black_hole_sound: black_hole_sound.play() # Play consumption sound
                        continue # No further pull if consumed

                    norm_obj = math.sqrt(dist_sq_obj) if dist_sq_obj > 0.001 else 1.0
                    pull_dir_x_obj = dx_obj_to_bh / norm_obj
                    pull_dir_y_obj = dy_obj_to_bh / norm_obj
                    pull_dir_z_obj = dz_obj_to_bh / norm_obj
                    
                    force_obj = bh.gravity_strength / (dist_sq_obj + 1.0) 
                    force_obj = min(force_obj, MAX_GRAVITY_FORCE_GENERAL) 
                    
                    # Apply force by directly modifying position (simplest for now)
                    # This assumes obj.x,y,z are view-relative world coordinates
                    obj.x += pull_dir_x_obj * force_obj * dt
                    obj.y += pull_dir_y_obj * force_obj * dt
                    obj.z += pull_dir_z_obj * force_obj * dt
        
        space_objects.extend(temp_particles_to_add_from_bh) # Add particles created by BH

        # Apply accumulated gravitational pull to player's movement parameters
        if player_health > 0: # Only if player is alive
            # Z-component of pull affects forward/backward thrust input
            # A positive player_acceleration_effect[2] means pull towards positive Z (further into scene)
            # This needs to be scaled appropriately to affect current_speed_z
            # current_speed_z is units/sec. player_acceleration_effect is effectively acceleration.
            current_speed_z -= player_acceleration_effect[2] * dt # If BH is in front (pos Z), effect[2] is pos, so speed_z decreases (slows down if moving away, speeds up if moving towards)
                                                              # If BH is behind (neg Z), effect[2] is neg, so speed_z increases (pushes player away from BH) - this needs to be pull_dir_z (towards BH)
                                                              # Let's re-think: effect[2] is ACCELERATION.
                                                              # If bh.z > player.z (0), pull_dir_z is positive. current_speed_z should become more positive.
            current_speed_z += player_acceleration_effect[2] * dt # Corrected: Add acceleration

            # X, Y components of pull affect view angles (yaw, pitch)
            # This creates a "drift" or "turn" towards the black hole.
            # Scale factor PLAYER_TURN_RESPONSE_TO_GRAVITY controls sensitivity.
            player_total_yaw_angle -= player_acceleration_effect[0] * PLAYER_TURN_RESPONSE_TO_GRAVITY * dt
            player_total_pitch_angle += player_acceleration_effect[1] * PLAYER_TURN_RESPONSE_TO_GRAVITY * dt # Pygame Y is inverted for screen, but pitch is generally standard

        # --- Collision Detection --- (Moved after gravity effects)
        _explosion_sound = explosion_sound if 'mixer_initialized' in locals() and mixer_initialized and 'explosion_sound' in locals() else None
        _player_hit_sound = player_hit_sound if 'mixer_initialized' in locals() and mixer_initialized and 'player_hit_sound' in locals() else None

        # Player Lasers vs Planets
        for laser in player_lasers_this_frame:
            if not laser.is_active: continue 
            for planet_obj in _initial_planets: # Use the list of actual Planet instances
                if not planet_obj.is_active: continue
                if not hasattr(planet_obj, 'health'): continue # Skip if planet doesn't have health

                dist_sq = (laser.x - planet_obj.x)**2 + (laser.y - planet_obj.y)**2 + (laser.z - planet_obj.z)**2
                if dist_sq < (planet_obj.world_radius + laser.world_radius)**2:
                    laser.is_active = False 
                    planet_obj.health -= 25 
                    impact_pos_x, impact_pos_y, impact_pos_z = laser.x, laser.y, laser.z
                    num_particles_for_planet_hit = NUM_PARTICLES_ON_EXPLOSION
                    if planet_obj.health <= 0:
                        planet_obj.is_active = False 
                        num_particles_for_planet_hit = NUM_PARTICLES_ON_EXPLOSION_PLANET # Bigger explosion
                        player_score += POINTS_PER_PLANET_DESTROYED # Award points for destroying planet
                    
                    if _explosion_sound: _explosion_sound.play()
                    for _ in range(num_particles_for_planet_hit):
                        p_vx,p_vy,p_vz = random_vector(PARTICLE_SPEED_MIN,PARTICLE_SPEED_MAX)
                        space_objects.append(Projectile(impact_pos_x, impact_pos_y, impact_pos_z, p_vx, p_vy, p_vz, PARTICLE_LIFESPAN, random.choice(PARTICLE_COLORS), PARTICLE_RADIUS, owner="neutral_explosion"))
                    break 
            if not laser.is_active: continue

        # Player Lasers vs Enemies
        for laser in player_lasers_this_frame:
            if not laser.is_active: continue 
            for enemy in active_enemies:
                if not enemy.is_active: continue
                dist_sq = (laser.x - enemy.x)**2 + (laser.y - enemy.y)**2 + (laser.z - enemy.z)**2
                if dist_sq < (enemy.world_radius + laser.world_radius)**2:
                    laser.is_active = False 
                    enemy.health -= 25 
                    if _player_hit_sound: _player_hit_sound.play() # Placeholder for enemy hit sound
                    if enemy.health <= 0:
                        enemy.is_active = False 
                        if _explosion_sound: _explosion_sound.play()
                        player_score += POINTS_PER_ENEMY_DESTROYED # Award points
                        for _ in range(NUM_PARTICLES_ON_EXPLOSION): 
                            p_vx,p_vy,p_vz = random_vector(PARTICLE_SPEED_MIN,PARTICLE_SPEED_MAX)
                            space_objects.append(Projectile(enemy.x, enemy.y, enemy.z, p_vx,p_vy,p_vz, PARTICLE_LIFESPAN, random.choice(PARTICLE_COLORS), PARTICLE_RADIUS, owner="neutral_explosion"))
                        # Add score logic here - already added above
                    break 
            if not laser.is_active: continue

        # Enemy Lasers vs Player
        for laser in enemy_lasers_this_frame:
            if not laser.is_active: continue 
            dist_sq_to_player = laser.x**2 + laser.y**2 + laser.z**2 # Player at origin
            if dist_sq_to_player < (PLAYER_HITBOX_RADIUS + laser.world_radius)**2:
                laser.is_active = False 
                player_health -= 10 
                if _player_hit_sound: _player_hit_sound.play()
                print(f"Player hit! Health: {player_health}")
                if player_health <= 0:
                    print("Game Over!")
                    running = False 
                break 
        
        # --- Enemy Spawning ---
        game_current_time_seconds_logic = pygame.time.get_ticks() / 1000.0
        if running and game_current_time_seconds_logic - last_enemy_spawn_time > ENEMY_SPAWN_INTERVAL and len(active_enemies) < MAX_ENEMIES:
            spawn_z_enemy = FAR_Z * 0.9 
            angle_enemy = random.uniform(0, 2 * math.pi) 
            radius_spread_enemy = FAR_Z * random.uniform(0.6, 0.9)
            spawn_x_enemy = radius_spread_enemy * math.cos(angle_enemy) 
            spawn_y_enemy = radius_spread_enemy * math.sin(angle_enemy) * (SCREEN_HEIGHT / SCREEN_WIDTH) 

            new_enemy = EnemyShip(spawn_x_enemy, spawn_y_enemy, spawn_z_enemy, ENEMY_COLOR, ENEMY_WORLD_RADIUS, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_FIRE_RATE, game_current_time_seconds_logic)
            active_enemies.append(new_enemy)
            space_objects.append(new_enemy) 
            last_enemy_spawn_time = game_current_time_seconds_logic
            # print(f"Spawned Enemy. Count: {len(active_enemies)}")

        # Comet Spawning
        if running and game_current_time_seconds_logic - last_comet_spawn_time > COMET_SPAWN_INTERVAL and len(active_comets) < MAX_COMETS:
            # Spawn comets from a side, moving across the screen
            side = random.choice([-1, 1]) # -1 for left, 1 for right
            spawn_x_comet = side * FAR_Z * random.uniform(0.8, 1.2) # Start off-screen horizontally
            spawn_y_comet = random.uniform(-FAR_Z * 0.3, FAR_Z * 0.3) * (SCREEN_HEIGHT/SCREEN_WIDTH)
            spawn_z_comet = random.uniform(FAR_Z * 0.5, FAR_Z * 0.9) # Start at a medium depth

            comet_speed = random.uniform(COMET_SPEED_MIN, COMET_SPEED_MAX)
            # Velocity aims generally towards the other side, with some variation
            vel_x_comet = -side * comet_speed * random.uniform(0.7, 1.0) 
            vel_y_comet = random.uniform(-comet_speed * 0.3, comet_speed * 0.3)
            vel_z_comet = random.uniform(-comet_speed * 0.2, comet_speed * 0.2) # Small Z velocity

            new_comet = Comet(spawn_x_comet, spawn_y_comet, spawn_z_comet,
                              COMET_HEAD_RADIUS, COMET_COLOR, (vel_x_comet, vel_y_comet, vel_z_comet),
                              COMET_TAIL_LENGTH, FOV_SCALE, SCREEN_WIDTH, SCREEN_HEIGHT, NEAR_Z_CLIP)
            active_comets.append(new_comet)
            space_objects.append(new_comet)
            last_comet_spawn_time = game_current_time_seconds_logic
            # print(f"Spawned Comet. Count: {len(active_comets)}")

        active_enemies = [e for e in active_enemies if e.is_active] 
        active_comets = [c for c in active_comets if c.is_active]

        # Update on-screen timer (display only)
        current_display_ticks = pygame.time.get_ticks()
        if current_display_ticks - last_second_tick >= 1000:
            game_time_seconds += 1
            if game_time_seconds > 999: game_time_seconds = 0 # Max display time for timer
            last_second_tick = current_display_ticks

        # --- Universe Reset Logic ---
        if game_time_seconds >= UNIVERSE_LIFESPAN_SECONDS:
            print(f"Universe lifespan of {UNIVERSE_LIFESPAN_SECONDS}s reached. Resetting universe...")

            # 1. Reset Player State
            player_health = PLAYER_MAX_HEALTH
            player_total_yaw_angle = 0.0
            player_total_pitch_angle = 0.0
            # Player speed/rotation speeds are reset by key input logic each frame, so no direct reset needed here.

            # 2. Clear Dynamic Objects
            active_enemies.clear() 
            _initial_planets.clear() # Clear the list of Planet instances

            # 3. Rebuild space_objects: Start with stars, then add new planets
            new_space_objects_list_after_reset = [] # Temp list for rebuilding
            for star_obj in stars: # 'stars' is the persistent list of Star instances
                star_obj.reset() # Reset each star's position
                new_space_objects_list_after_reset.append(star_obj)
            
            # Re-create initial planets (or generate new random ones)
            # This example re-creates them as defined at the start of main()
            # Ensure Planet class is available and health is handled if it was modified previously
            planet1 = Planet(x=0, y=0, z=1000, color=REDDISH_PLANET, world_radius=100, health=100)
            _initial_planets.append(planet1)

            planet2 = Planet(x=1200, y=300, z=1800, color=BLUEISH_PLANET, world_radius=150, health=100)
            _initial_planets.append(planet2)
            
            planet3 = Planet(x=-800, y=-400, z=1200, color=GREENISH_PLANET, world_radius=80, health=100)
            _initial_planets.append(planet3)

            planet4 = Planet(x=200, y=1000, z=2500, color=GREY, world_radius=120, health=100)
            _initial_planets.append(planet4)
            
            new_space_objects_list_after_reset.extend(_initial_planets)
            space_objects = new_space_objects_list_after_reset # Assign the rebuilt list

            # 4. Reset Timers
            game_time_seconds = 0 # Reset the display/universe timer
            # Reset enemy, comet, and black hole spawn timers relative to current actual game time
            game_current_time_seconds_logic = pygame.time.get_ticks() / 1000.0
            last_enemy_spawn_time = game_current_time_seconds_logic 
            last_comet_spawn_time = game_current_time_seconds_logic 
            last_black_hole_spawn_time = game_current_time_seconds_logic # Reset BH timer

            # 5. Sound Effect
            _universe_reset_sound = universe_reset_sound if 'mixer_initialized' in locals() and mixer_initialized and 'universe_reset_sound' in locals() and universe_reset_sound else None
            if _universe_reset_sound:
                _universe_reset_sound.play()
            
            print("Universe reset complete.")
            # Optional: Add a brief visual cue like a screen flash (e.g., fill screen white for a moment)
            # screen.fill(WHITE)
            # pygame.display.flip()
            # pygame.time.wait(100) # Pause for 100ms for the flash effect


        space_objects.sort(key=lambda obj: obj.z, reverse=True) # Sort for drawing

        # --- Drawing ---
        screen.fill(BLACK)
        for obj in space_objects:
            if obj.is_active: 
                obj.draw(screen) 
        draw_cockpit(screen)

        # Display Player Health
        health_color = WHITE if player_health > (PLAYER_MAX_HEALTH * 0.25) else REDDISH_PLANET
        health_text_surface = player_health_display_font.render(f"Player Health: {max(0, player_health)}", True, health_color)
        screen.blit(health_text_surface, (SCREEN_WIDTH - health_text_surface.get_width() - 10, 10))

        # Display Score
        score_text_surface = score_font.render(f"Score: {int(player_score)}", True, WHITE)
        # Position score below health or timer, e.g.
        score_pos_y = health_text_surface.get_height() + 15 
        screen.blit(score_text_surface, (SCREEN_WIDTH - score_text_surface.get_width() - 10, score_pos_y))
        
        time_text_surface = time_font.render(f"Time: {game_time_seconds}", True, WHITE)
        screen.blit(time_text_surface, (10, 10))

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
