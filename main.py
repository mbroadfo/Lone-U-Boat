# Lone U-Boat Game

import pygame
import math

# --- CONSTANTS ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900
HEX_SIZE = 40

# --- COLORS ---
DEEP_WATER_BLUE = (25, 25, 112)
SHALLOW_WATER_TEAL = (64, 224, 208)
LAND_GREEN = (34, 139, 34)
OUT_OF_BOUNDS_WHITE = (255, 255, 255)
BORDER_BLACK = (0, 0, 0)
BACKGROUND_GRAY = (211, 211, 211) # Light gray for the background
PANEL_GRAY = (100, 100, 100)
BOX_GRAY = (150, 150, 150)
TEXT_WHITE = (255, 255, 255)
TEXT_BLACK = (0, 0, 0)
TEXT_GREEN = (0, 255, 0)
TEXT_YELLOW = (255, 255, 0)
TEXT_RED = (255, 0, 0)

# --- TERRAIN TYPES ---
DEEP_WATER = 1
SHALLOW_WATER = 2
LAND = 3
OUT_OF_BOUNDS = 0

# --- MAP LAYOUT ---
game_map = [
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 2, 2, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 2, 3, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 2, 3, 2, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 2, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
]

terrain_colors = {
    DEEP_WATER: DEEP_WATER_BLUE,
    SHALLOW_WATER: SHALLOW_WATER_TEAL,
    LAND: LAND_GREEN,
    OUT_OF_BOUNDS: OUT_OF_BOUNDS_WHITE
}

# --- GAME STATE (placeholders) ---
game_state = {
    "uboat_pos": (7, 7), # Initial position (row, col)
    "uboat_orientation": 0, # 0-5, starting pointing right
    "detection_level": 1, # 0: Silent, 1: Aware, 2: Traced, 3: Locked
    "hull_damage": 2, # 0: OK, 1: DeepX, 2: MedX, 3: PeriX, 4: Destroyed
    "torpedo_tubes": {
        "1": "loaded", "2": "loaded", "3": "empty", "4": "damaged", "5": "loaded"
    },
    "crew_status": {
        "Captain": "OK", "Sonar Operator": "OK", "Engineer": "KIA", 
        "Weapons Officer": "OK", "Lookout": "OK", "Med Officer": "OK"
    },
    "system_damage": {
        "Engine": "damaged", "Flak Gun": "OK", "Deck Gun": "OK"
    }
}

# --- SPRITE CLASSES ---
class Uboat(pygame.sprite.Sprite):
    """Represents the player's U-Boat."""
    def __init__(self, initial_pos, initial_orientation, hex_size):
        super().__init__()
        self.row, self.col = initial_pos
        self.orientation = initial_orientation # 0-5, 0 is right, increasing clockwise
        self.hex_size = hex_size

        # Load and scale the image
        try:
            self.original_image = pygame.image.load("assets/UB-Surfaced.png").convert_alpha()
            # Rotate the base image so the top is pointing right (0 degrees)
            self.original_image = pygame.transform.rotate(self.original_image, -90)
            # Scale the image so its width is 80% of the hex diameter
            scale_factor = (self.hex_size * 1.8) / self.original_image.get_width()
            new_width = int(self.original_image.get_width() * scale_factor)
            new_height = int(self.original_image.get_height() * scale_factor)
            self.original_image = pygame.transform.scale(self.original_image, (new_width, new_height))
        except pygame.error as e:
            print(f"Unable to load U-Boat image: {e}")
            # Create a fallback red rectangle if image fails to load
            self.original_image = pygame.Surface((self.hex_size, self.hex_size // 2))
            self.original_image.fill(TEXT_RED)

        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.update_position_and_orientation()

    def turn(self, direction):
        """Turn the U-Boat. direction is 1 for CW, -1 for CCW."""
        self.orientation = (self.orientation + direction + 6) % 6
        self.update_position_and_orientation()

    def move_forward(self):
        """Move the U-Boat one hex in its current direction."""
        # Cube directions: (q, r, s) where q+r+s=0
        cube_directions = [
            (+1, -1, 0), # NE
            (+1, 0, -1), # E
            (0, +1, -1), # SE
            (-1, +1, 0), # SW
            (-1, 0, +1), # W
            (0, -1, +1), # NW
        ]
        # Our orientation: 0:E, 1:SE, 2:SW, 3:W, 4:NW, 5:NE
        orientation_to_cube_map = [1, 2, 3, 4, 5, 0]

        # Convert offset to cube
        q = self.col - (self.row - (self.row & 1)) // 2
        r = self.row
        s = -q - r

        # Get change from our orientation
        dq, dr, ds = cube_directions[orientation_to_cube_map[self.orientation]]

        # Calculate new cube coordinates
        new_q, new_r, new_s = q + dq, r + dr, s + ds

        # Convert back to offset
        new_row = new_r
        new_col = new_q + (new_r - (new_r & 1)) // 2
        
        # Check if the new position is valid (within bounds and not land)
        if 0 <= new_row < len(game_map) and 0 <= new_col < len(game_map[0]):
            terrain = game_map[new_row][new_col]
            # Only allow movement into water hexes (DEEP_WATER or SHALLOW_WATER)
            if terrain == DEEP_WATER or terrain == SHALLOW_WATER:
                self.row = new_row
                self.col = new_col
                self.update_position_and_orientation()
            # else: move blocked by land or out-of-bounds
        # else: move blocked by map edge

    def update_position_and_orientation(self):
        """Recalculates the screen position and rotates the image."""
        # Pygame rotates counter-clockwise. Angle 0 is right.
        angle = -60 * self.orientation
        self.image = pygame.transform.rotate(self.original_image, angle)
        
        # Calculate screen position based on hex grid coordinates
        hex_width = self.hex_size * math.sqrt(3)
        hex_height = self.hex_size * 2
        x_offset = hex_width / 2 if self.row % 2 != 0 else 0
        
        center_x = self.col * hex_width + x_offset + hex_width / 2
        center_y = self.row * hex_height * 0.75 + hex_height / 2
        
        self.rect = self.image.get_rect(center=(center_x, center_y))

# --- DRAWING FUNCTIONS ---

def draw_hex(surface, x, y, size, color, border_color, width=1):
    """Draws a filled hexagon with a border."""
    points = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.pi / 180 * angle_deg
        points.append((x + size * math.cos(angle_rad),
                       y + size * math.sin(angle_rad)))
    pygame.draw.polygon(surface, color, points, 0)
    pygame.draw.polygon(surface, border_color, points, width)

def create_hex_grid_surface(map_data, hex_size):
    """Creates a surface with the rendered hex grid based on map data."""
    hex_width = hex_size * math.sqrt(3)
    hex_height = hex_size * 2
    map_height = len(map_data)
    map_width = len(map_data[0]) if map_height > 0 else 0
    total_width = map_width * hex_width + hex_width / 2
    total_height = (map_height * hex_height * 0.75) + (hex_height * 0.25)
    grid_surface = pygame.Surface((total_width, total_height))
    grid_surface.fill(OUT_OF_BOUNDS_WHITE)

    for row, row_data in enumerate(map_data):
        for col, terrain in enumerate(row_data):
            x_offset = hex_width / 2 if row % 2 != 0 else 0
            x = col * hex_width + x_offset + hex_width / 2
            y = row * hex_height * 0.75 + hex_height / 2
            color = terrain_colors.get(terrain, OUT_OF_BOUNDS_WHITE)
            draw_hex(grid_surface, x, y, hex_size, color, BORDER_BLACK)
            
    return grid_surface

def draw_ui_box(surface, rect, title, font_title):
    """Draws a titled box."""
    pygame.draw.rect(surface, PANEL_GRAY, rect, 2)
    title_surf = font_title.render(title, True, TEXT_BLACK)
    title_rect = title_surf.get_rect(centerx=rect.centerx, y=rect.y - 25)
    surface.blit(title_surf, title_rect)

def draw_track(surface, rect, labels, current_index, font):
    """Draws a horizontal track with an indicator."""
    box_width = rect.width / len(labels)
    for i, label in enumerate(labels):
        box_rect = pygame.Rect(rect.x + i * box_width, rect.y, box_width, rect.height)
        pygame.draw.rect(surface, BOX_GRAY, box_rect, 1)
        if i == current_index:
            pygame.draw.rect(surface, TEXT_RED, box_rect.inflate(-4, -4))
        
        label_surf = font.render(label, True, TEXT_BLACK)
        label_rect = label_surf.get_rect(center=box_rect.center)
        surface.blit(label_surf, label_rect)

def draw_detection_level(surface, rect, game_state, fonts):
    """UI for Detection Level."""
    draw_ui_box(surface, rect, "DETECTION LEVEL", fonts["title"])
    labels = ["Silent", "Aware", "Traced", "Locked"]
    draw_track(surface, rect, labels, game_state["detection_level"], fonts["text"])

def draw_hull_damage(surface, rect, game_state, fonts):
    """UI for Hull Damage."""
    draw_ui_box(surface, rect, "HULL DAMAGE", fonts["title"])
    labels = ["OK", "DeepX", "MedX", "PeriX", "Dead"]
    draw_track(surface, rect, labels, game_state["hull_damage"], fonts["text"])

def draw_torpedo_tubes(surface, rect, game_state, fonts):
    """UI for Torpedo Tubes."""
    draw_ui_box(surface, rect, "TORPEDO TUBES", fonts["title"])
    tubes = game_state["torpedo_tubes"]
    box_width = rect.width / len(tubes)
    for i, (tube_num, status) in enumerate(tubes.items()):
        box_rect = pygame.Rect(rect.x + i * box_width, rect.y, box_width, rect.height)
        pygame.draw.rect(surface, BOX_GRAY, box_rect, 1)
        
        color = TEXT_GREEN if status == "loaded" else (TEXT_YELLOW if status == "empty" else TEXT_RED)
        pygame.draw.rect(surface, color, box_rect.inflate(-4, -4))

        num_surf = fonts["text_bold"].render(tube_num, True, TEXT_BLACK)
        num_rect = num_surf.get_rect(centerx=box_rect.centerx, y=box_rect.y + 5)
        surface.blit(num_surf, num_rect)

def draw_crew_status(surface, rect, game_state, fonts):
    """UI for Crew Status."""
    draw_ui_box(surface, rect, "CREW STATUS", fonts["title"])
    crew = game_state["crew_status"]
    box_width = rect.width / len(crew)
    for i, (name, status) in enumerate(crew.items()):
        box_rect = pygame.Rect(rect.x + i * box_width, rect.y, box_width, rect.height)
        pygame.draw.rect(surface, BOX_GRAY, box_rect, 1)
        
        if status != "OK":
            pygame.draw.line(surface, TEXT_RED, (box_rect.left, box_rect.top), (box_rect.right, box_rect.bottom), 3)
            pygame.draw.line(surface, TEXT_RED, (box_rect.right, box_rect.top), (box_rect.left, box_rect.bottom), 3)

        name_surf = fonts["text_small"].render(name, True, TEXT_BLACK)
        name_rect = name_surf.get_rect(center=box_rect.center)
        surface.blit(name_surf, name_rect)

def draw_system_damage(surface, rect, game_state, fonts):
    """UI for System Damage."""
    draw_ui_box(surface, rect, "SYSTEM DAMAGE", fonts["title"])
    systems = game_state["system_damage"]
    box_height = rect.height / len(systems)
    for i, (name, status) in enumerate(systems.items()):
        box_rect = pygame.Rect(rect.x, rect.y + i * box_height, rect.width, box_height)
        pygame.draw.rect(surface, BOX_GRAY, box_rect, 1)

        if status != "OK":
             pygame.draw.rect(surface, TEXT_RED, box_rect.inflate(-4, -4))

        name_surf = fonts["text"].render(name, True, TEXT_BLACK)
        name_rect = name_surf.get_rect(center=box_rect.center)
        surface.blit(name_surf, name_rect)

# --- MAIN FUNCTION ---
def main():
    """Main function for the game."""
    pygame.init()

    # Set up fonts
    fonts = {
        "title": pygame.font.SysFont("Arial", 20, bold=True),
        "text": pygame.font.SysFont("Arial", 16),
        "text_bold": pygame.font.SysFont("Arial", 18, bold=True),
        "text_small": pygame.font.SysFont("Arial", 12)
    }

    # Set up the display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Lone U-Boat")

    # Create the map surface and center it
    map_surface = create_hex_grid_surface(game_map, HEX_SIZE)
    map_rect = map_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

    # Create the U-Boat
    uboat = Uboat(game_state["uboat_pos"], game_state["uboat_orientation"], HEX_SIZE)
    uboat_sprite_group = pygame.sprite.GroupSingle(uboat)

    # Define UI element rectangles
    detection_rect = pygame.Rect(50, 50, 300, 40)
    hull_rect = pygame.Rect(50, 120, 300, 40)
    torpedo_rect = pygame.Rect(SCREEN_WIDTH - 350, 50, 300, 60)
    crew_rect = pygame.Rect(50, SCREEN_HEIGHT - 100, 700, 50)
    damage_rect = pygame.Rect(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200, 150, 150)

    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d: # Turn Clockwise
                    uboat.turn(1)
                if event.key == pygame.K_a: # Turn Counter-Clockwise
                    uboat.turn(-1)
                if event.key == pygame.K_w: # Move Forward
                    uboat.move_forward()

        # --- Drawing ---
        screen.fill(BACKGROUND_GRAY)
        
        # Draw map
        screen.blit(map_surface, map_rect)

        # Draw U-Boat on the map, adjusting for the map's position
        uboat_draw_pos = uboat.rect.move(map_rect.topleft)
        screen.blit(uboat.image, uboat_draw_pos)
        
        # Draw UI elements
        draw_detection_level(screen, detection_rect, game_state, fonts)
        draw_hull_damage(screen, hull_rect, game_state, fonts)
        draw_torpedo_tubes(screen, torpedo_rect, game_state, fonts)
        draw_crew_status(screen, crew_rect, game_state, fonts)
        draw_system_damage(screen, damage_rect, game_state, fonts)

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
