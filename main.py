# Lone U-Boat Game

import pygame
import math

# --- CONSTANTS ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 850
HEX_SIZE = 45

# Layout zones
TOP_PANEL_HEIGHT = 120
BOTTOM_PANEL_HEIGHT = 140
SIDE_PANEL_WIDTH = 200

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

# --- MAP LAYOUT (9 wide × 10 tall with corner cutouts) ---
# None = cutout for UI panels
game_map = [
    [None, None, 1, 1, 1, 1, 1, None, None],
    [None, 1, 1, 2, 1, 1, 1, 1, None],
    [1, 1, 2, 2, 3, 2, 1, 1, 1],
    [1, 1, 2, 3, 3, 2, 2, 1, 1],
    [1, 1, 1, 2, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 1, 2, 3, 2, 1],
    [1, 1, 1, 1, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 2, 3, 2, 1, 1],
    [None, 1, 1, 1, 2, 2, 1, 1, None],
    [None, None, 1, 1, 1, 1, 1, None, None],
]

terrain_colors = {
    DEEP_WATER: DEEP_WATER_BLUE,
    SHALLOW_WATER: SHALLOW_WATER_TEAL,
    LAND: LAND_GREEN,
    OUT_OF_BOUNDS: OUT_OF_BOUNDS_WHITE
}

# --- GAME STATE ---
game_state = {
    "mission_number": 9,
    "uboat_pos": (5, 4), # Initial position (row, col)
    "uboat_orientation": 0, # 0-5, starting pointing right
    "uboat_depth": 0, # 0=Surfaced, 1=Periscope, 2=Medium, 3=Deep
    "detection_level": 1, # 0: Silent, 1: Aware, 2: Traced, 3: Locked
    "hull_damage": 2, # 1: DeepX, 2: MedX, 3: PeriX, 4: Dead
    "torpedo_tubes": {
        "1": "loaded", "2": "loaded", "3": "loaded", "4": "loaded", "5": "loaded"
    },
    "crew_status": {
        "1-Captain": "OK",
        "2-Sonar Operator": "OK",
        "3-Engineer": "KIA",
        "4-Weapons Officer": "OK",
        "5-Look Out": "OK",
        "6-Med Officer": "OK"
    },
    "system_damage": {
        "Engine": "damaged",
        "Flak Gun": "OK",
        "Deck Gun": "OK"
    },
    "ships": {
        "corvette": (7, 2),
        "destroyer": (8, 6),
    },
    "anchor_pos": (6, 4),
    "command_input": "",
    "message": "Enter commands (M,R,L,A,D,F,G,Tn,Fn) and press Enter"
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
            # Only allow movement into water hexes (DEEP_WATER or SHALLOW_WATER), not None cutouts
            if terrain == DEEP_WATER or terrain == SHALLOW_WATER:
                self.row = new_row
                self.col = new_col
                self.update_position_and_orientation()
            # else: move blocked by land, out-of-bounds, or cutout
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
    grid_surface = pygame.Surface((total_width, total_height), pygame.SRCALPHA)
    grid_surface.fill((0, 0, 0, 0))  # Transparent

    for row, row_data in enumerate(map_data):
        for col, terrain in enumerate(row_data):
            if terrain is None:  # Skip cutout hexes
                continue
            x_offset = hex_width / 2 if row % 2 != 0 else 0
            x = col * hex_width + x_offset + hex_width / 2
            y = row * hex_height * 0.75 + hex_height / 2
            color = terrain_colors.get(terrain, OUT_OF_BOUNDS_WHITE)
            draw_hex(grid_surface, x, y, hex_size, color, BORDER_BLACK)
            
    return grid_surface

def draw_mission_number(surface, mission_num, fonts):
    """Draw mission number centered at top."""
    text = fonts["title"].render(f"MISSION {mission_num}", True, TEXT_BLACK)
    rect = text.get_rect(centerx=SCREEN_WIDTH // 2, y=10)
    pygame.draw.rect(surface, TEXT_WHITE, rect.inflate(20, 10))
    pygame.draw.rect(surface, BORDER_BLACK, rect.inflate(20, 10), 2)
    surface.blit(text, rect)

def draw_detection_and_hull(surface, game_state, fonts):
    """Draw detection level and hull damage in upper left."""
    x, y = 10, 50
    
    # Detection Level Track
    pygame.draw.rect(surface, TEXT_WHITE, (x, y, 180, 50))
    pygame.draw.rect(surface, BORDER_BLACK, (x, y, 180, 50), 2)
    title = fonts["text_small"].render("DETECTION LEVEL", True, TEXT_BLACK)
    surface.blit(title, (x + 5, y + 2))
    
    labels = ["0\nSilent", "1\nAware", "2\nTraced", "3\nLocked"]
    box_w = 40
    for i, label in enumerate(labels):
        box_rect = pygame.Rect(x + 5 + i * box_w, y + 20, box_w, 25)
        color = TEXT_RED if i == game_state["detection_level"] else BOX_GRAY
        pygame.draw.rect(surface, color, box_rect)
        pygame.draw.rect(surface, BORDER_BLACK, box_rect, 1)
        txt = fonts["text_small"].render(str(i), True, TEXT_BLACK)
        surface.blit(txt, (box_rect.centerx - 5, box_rect.centery - 7))
    
    # Hull Damage Track
    y += 60
    pygame.draw.rect(surface, TEXT_WHITE, (x, y, 180, 50))
    pygame.draw.rect(surface, BORDER_BLACK, (x, y, 180, 50), 2)
    title = fonts["text_small"].render("HULL DAMAGE", True, TEXT_BLACK)
    surface.blit(title, (x + 5, y + 2))
    
    labels = ["1\nDeepX", "2\nMedX", "3\nPeriX", "4\nDead"]
    for i, label in enumerate(labels, 1):
        box_rect = pygame.Rect(x + 5 + (i-1) * box_w, y + 20, box_w, 25)
        color = TEXT_RED if i == game_state["hull_damage"] else BOX_GRAY
        pygame.draw.rect(surface, color, box_rect)
        pygame.draw.rect(surface, BORDER_BLACK, box_rect, 1)
        txt = fonts["text_small"].render(str(i), True, TEXT_BLACK)
        surface.blit(txt, (box_rect.centerx - 5, box_rect.centery - 7))

def draw_torpedo_tubes_panel(surface, game_state, fonts):
    """Draw torpedo tubes in upper right."""
    x = SCREEN_WIDTH - 190
    y = 50
    
    pygame.draw.rect(surface, TEXT_WHITE, (x, y, 180, 90))
    pygame.draw.rect(surface, BORDER_BLACK, (x, y, 180, 90), 2)
    title = fonts["text_small"].render("TORPEDO TUBES", True, TEXT_BLACK)
    surface.blit(title, (x + 5, y + 2))
    
    # Forward tubes 1-4
    tubes = game_state["torpedo_tubes"]
    box_w = 40
    for i in range(1, 5):
        status = tubes[str(i)]
        box_rect = pygame.Rect(x + 5 + (i-1) * box_w, y + 25, box_w, 25)
        color = TEXT_GREEN if status == "loaded" else (TEXT_YELLOW if status == "empty" else TEXT_RED)
        pygame.draw.rect(surface, color, box_rect)
        pygame.draw.rect(surface, BORDER_BLACK, box_rect, 1)
        txt = fonts["text"].render("F", True, TEXT_BLACK)
        surface.blit(txt, (box_rect.centerx - 5, box_rect.centery - 7))
    
    # Rear tube 5
    status = tubes["5"]
    box_rect = pygame.Rect(x + 70, y + 55, 40, 25)
    color = TEXT_GREEN if status == "loaded" else (TEXT_YELLOW if status == "empty" else TEXT_RED)
    pygame.draw.rect(surface, color, box_rect)
    pygame.draw.rect(surface, BORDER_BLACK, box_rect, 1)
    txt = fonts["text"].render("R\n5", True, TEXT_BLACK)
    surface.blit(txt, (box_rect.centerx - 5, box_rect.centery - 7))

def draw_crew_panel(surface, game_state, fonts):
    """Draw crew status in lower left corner."""
    x, y = 10, SCREEN_HEIGHT - 130
    
    pygame.draw.rect(surface, TEXT_WHITE, (x, y, 260, 120))
    pygame.draw.rect(surface, BORDER_BLACK, (x, y, 260, 120), 2)
    title = fonts["text_small"].render("CREW STATUS", True, TEXT_BLACK)
    surface.blit(title, (x + 5, y + 2))
    
    crew = game_state["crew_status"]
    box_w = 80
    box_h = 35
    for i, (name, status) in enumerate(crew.items()):
        row = i // 3
        col = i % 3
        box_rect = pygame.Rect(x + 10 + col * box_w, y + 25 + row * box_h, box_w - 5, box_h - 5)
        pygame.draw.rect(surface, BOX_GRAY, box_rect)
        pygame.draw.rect(surface, BORDER_BLACK, box_rect, 2)
        
        # Draw KIA marker if dead
        if status != "OK":
            pygame.draw.line(surface, TEXT_RED, (box_rect.left + 3, box_rect.top + 3), 
                           (box_rect.right - 3, box_rect.bottom - 3), 3)
            pygame.draw.line(surface, TEXT_RED, (box_rect.right - 3, box_rect.top + 3), 
                           (box_rect.left + 3, box_rect.bottom - 3), 3)
        
        txt = fonts["text_small"].render(name, True, TEXT_BLACK)
        txt_rect = txt.get_rect(center=box_rect.center)
        surface.blit(txt, txt_rect)

def draw_system_damage_panel(surface, game_state, fonts):
    """Draw system damage in lower right corner."""
    x = SCREEN_WIDTH - 190
    y = SCREEN_HEIGHT - 130
    
    pygame.draw.rect(surface, TEXT_WHITE, (x, y, 180, 120))
    pygame.draw.rect(surface, BORDER_BLACK, (x, y, 180, 120), 2)
    title = fonts["text_small"].render("SYSTEM DAMAGE", True, TEXT_BLACK)
    surface.blit(title, (x + 5, y + 2))
    
    systems = game_state["system_damage"]
    box_h = 30
    for i, (name, status) in enumerate(systems.items()):
        box_rect = pygame.Rect(x + 10, y + 25 + i * box_h, 160, box_h - 5)
        color = TEXT_RED if status != "OK" else BOX_GRAY
        pygame.draw.rect(surface, color, box_rect)
        pygame.draw.rect(surface, BORDER_BLACK, box_rect, 2)
        
        txt = fonts["text"].render(name, True, TEXT_BLACK)
        txt_rect = txt.get_rect(center=box_rect.center)
        surface.blit(txt, txt_rect)

def draw_ship_markers(surface, hex_size, map_rect, game_state, font):
    """Draw ship position markers on the map."""
    hex_width = hex_size * math.sqrt(3)
    hex_height = hex_size * 2
    
    # Draw ships
    for ship_name, (row, col) in game_state.get("ships", {}).items():
        x_offset = hex_width / 2 if row % 2 != 0 else 0
        x = col * hex_width + x_offset + hex_width / 2
        y = row * hex_height * 0.75 + hex_height / 2
        
        letter = ship_name[0].upper()  # C for Corvette, D for Destroyer
        text = font.render(letter, True, TEXT_YELLOW)
        text_rect = text.get_rect(center=(x + map_rect.left, y + map_rect.top))
        surface.blit(text, text_rect)
    
    # Draw anchor
    anchor_pos = game_state.get("anchor_pos")
    if anchor_pos:
        row, col = anchor_pos
        x_offset = hex_width / 2 if row % 2 != 0 else 0
        x = col * hex_width + x_offset + hex_width / 2
        y = row * hex_height * 0.75 + hex_height / 2
        
        text = font.render("⚓", True, TEXT_WHITE)
        text_rect = text.get_rect(center=(x + map_rect.left, y + map_rect.top))
        surface.blit(text, text_rect)

def draw_command_input(surface, game_state, fonts):
    """Draw command input box at bottom center."""
    x = 280
    y = SCREEN_HEIGHT - 50
    width = 440
    height = 40
    
    # Draw input box
    pygame.draw.rect(surface, TEXT_WHITE, (x, y, width, height))
    pygame.draw.rect(surface, BORDER_BLACK, (x, y, width, height), 2)
    
    # Draw label
    label = fonts["text_small"].render("Commands:", True, TEXT_BLACK)
    surface.blit(label, (x + 5, y - 15))
    
    # Draw input text
    input_text = fonts["text"].render(game_state["command_input"], True, TEXT_BLACK)
    surface.blit(input_text, (x + 5, y + 10))
    
    # Draw message/feedback
    msg = fonts["text_small"].render(game_state["message"], True, TEXT_BLACK)
    msg_rect = msg.get_rect(centerx=SCREEN_WIDTH // 2, y=y + height + 5)
    surface.blit(msg, msg_rect)

def execute_commands(command_string, uboat, game_state):
    """Parse and execute a sequence of commands."""
    commands = [cmd.strip().upper() for cmd in command_string.split(',')]
    messages = []
    
    for cmd in commands:
        if not cmd:
            continue
            
        if cmd == 'M':
            # Move forward
            old_pos = (uboat.row, uboat.col)
            uboat.move_forward()
            if (uboat.row, uboat.col) != old_pos:
                messages.append(f"Moved to ({uboat.row},{uboat.col})")
            else:
                messages.append("Move blocked!")
                
        elif cmd == 'R':
            # Turn right
            uboat.turn(1)
            messages.append(f"Turned right (facing {uboat.orientation})")
            
        elif cmd == 'L':
            # Turn left
            uboat.turn(-1)
            messages.append(f"Turned left (facing {uboat.orientation})")
            
        elif cmd == 'A':
            # Ascend
            if game_state["uboat_depth"] > 0:
                game_state["uboat_depth"] -= 1
                depth_names = ["Surfaced", "Periscope", "Medium", "Deep"]
                messages.append(f"Ascended to {depth_names[game_state['uboat_depth']]}")
            else:
                messages.append("Already at surface!")
                
        elif cmd == 'D':
            # Descend
            if game_state["uboat_depth"] < 3:
                game_state["uboat_depth"] += 1
                depth_names = ["Surfaced", "Periscope", "Medium", "Deep"]
                messages.append(f"Descended to {depth_names[game_state['uboat_depth']]}")
            else:
                messages.append("Already at max depth!")
                
        elif cmd == 'F':
            # Fix/Repair (placeholder)
            messages.append("Repair initiated")
            
        elif cmd == 'G':
            # Fire deck gun (placeholder)
            messages.append("Deck gun fired!")
            
        elif cmd.startswith('T') and len(cmd) == 2 and cmd[1].isdigit():
            # Load torpedo tube
            tube = cmd[1]
            if tube in game_state["torpedo_tubes"]:
                game_state["torpedo_tubes"][tube] = "loaded"
                messages.append(f"Loaded tube {tube}")
            else:
                messages.append(f"Invalid tube {tube}")
                
        elif cmd.startswith('F') and len(cmd) == 2 and cmd[1].isdigit():
            # Fire torpedo tube
            tube = cmd[1]
            if tube in game_state["torpedo_tubes"]:
                if game_state["torpedo_tubes"][tube] == "loaded":
                    game_state["torpedo_tubes"][tube] = "empty"
                    messages.append(f"Fired tube {tube}!")
                else:
                    messages.append(f"Tube {tube} not loaded!")
            else:
                messages.append(f"Invalid tube {tube}")
        else:
            messages.append(f"Unknown command: {cmd}")
    
    return " | ".join(messages) if messages else "No commands executed"

# --- MAIN FUNCTION ---
def main():
    """Main function for the game."""
    pygame.init()

    # Set up fonts
    fonts = {
        "title": pygame.font.SysFont("Arial", 20, bold=True),
        "text": pygame.font.SysFont("Arial", 16),
        "text_bold": pygame.font.SysFont("Arial", 18, bold=True),
        "text_small": pygame.font.SysFont("Arial", 11),
        "marker": pygame.font.SysFont("Arial", 24, bold=True)
    }

    # Set up the display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Lone U-Boat")

    # Create the map surface and center it
    map_surface = create_hex_grid_surface(game_map, HEX_SIZE)
    map_rect = map_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))

    # Create the U-Boat
    uboat = Uboat(game_state["uboat_pos"], game_state["uboat_orientation"], HEX_SIZE)

    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                # Command input handling
                if event.key == pygame.K_RETURN:
                    # Execute commands
                    if game_state["command_input"]:
                        result_msg = execute_commands(game_state["command_input"], uboat, game_state)
                        game_state["message"] = result_msg
                        game_state["command_input"] = ""
                elif event.key == pygame.K_BACKSPACE:
                    game_state["command_input"] = game_state["command_input"][:-1]
                elif event.key == pygame.K_ESCAPE:
                    game_state["command_input"] = ""
                    game_state["message"] = "Commands cleared"
                elif event.unicode and len(game_state["command_input"]) < 50:
                    # Add character to input
                    game_state["command_input"] += event.unicode
                
                # Direct controls (for testing/convenience)
                if event.key == pygame.K_d:
                    uboat.turn(1)
                if event.key == pygame.K_a:
                    uboat.turn(-1)
                if event.key == pygame.K_w:
                    uboat.move_forward()

        # --- Drawing ---
        screen.fill(BACKGROUND_GRAY)
        
        # Draw mission number at top
        draw_mission_number(screen, game_state["mission_number"], fonts)
        
        # Draw map
        screen.blit(map_surface, map_rect)

        # Draw ship markers and anchor
        draw_ship_markers(screen, HEX_SIZE, map_rect, game_state, fonts["marker"])

        # Draw U-Boat on the map, adjusting for the map's position
        uboat_draw_pos = uboat.rect.move(map_rect.topleft)
        screen.blit(uboat.image, uboat_draw_pos)
        
        # Draw UI panels in corners
        draw_detection_and_hull(screen, game_state, fonts)
        draw_torpedo_tubes_panel(screen, game_state, fonts)
        draw_crew_panel(screen, game_state, fonts)
        draw_system_damage_panel(screen, game_state, fonts)
        
        # Draw command input box
        draw_command_input(screen, game_state, fonts)

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
