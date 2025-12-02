import pygame
import random
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
import heapq
from collections import defaultdict

# Initialisation Pygame
pygame.init()

# Constantes
WIDTH, HEIGHT = 1300, 800
FPS = 60
TILE_SIZE = 20  # Grille pour pathfinding

# Timing
CYCLE_DURATION = 120  # 2 minutes
CLEANING_BASE_TIME = 2  # Base en secondes
CHARGING_RATE = 20  # % par seconde
EMPTYING_TIME = 2

# Batterie et ressources
MAX_BATTERY = 100
BATTERY_DRAIN_MOVE = 0.3  # Par seconde
BATTERY_DRAIN_CLEAN_BASE = 1.5  # Par seconde
MAX_DIRT_CAPACITY = 100
DIRT_PER_CLEAN = 25

# Couleurs modernes
class Colors:
    BG = (15, 23, 42)
    FLOOR = (30, 41, 59)
    WALL = (51, 65, 85)
    ROBOT = (59, 130, 246)
    ROBOT_GLOW = (96, 165, 250)
    TEXT = (248, 250, 252)
    PANEL = (30, 41, 59)
    PANEL_ACCENT = (51, 65, 85)
    
    CLEAN = (34, 197, 94)
    DUSTY = (251, 191, 36)
    DIRTY = (249, 115, 22)
    VERY_DIRTY = (239, 68, 68)
    
    OBSTACLE = (100, 116, 139)
    STATION = (147, 51, 234)
    PATH = (59, 130, 246, 100)

class DirtLevel(Enum):
    CLEAN = 0
    DUSTY = 1      # Poussière
    DIRTY = 2      # Détritus
    VERY_DIRTY = 3 # Grosse saleté

class AgentState(Enum):
    IDLE = "repos"
    MOVING = "déplacement"
    CLEANING = "nettoyage"
    CHARGING = "recharge"
    EMPTYING = "vidage"
    RETURNING = "retour station"

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    color: Tuple[int, int, int]

@dataclass
class Node:
    """Noeud pour A*"""
    x: int
    y: int
    g: float = float('inf')  # Coût depuis le départ
    h: float = 0  # Heuristique vers l'arrivée
    parent: Optional['Node'] = None
    
    @property
    def f(self):
        return self.g + self.h
    
    def __lt__(self, other):
        return self.f < other.f
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

class Obstacle:
    """Obstacle (meuble)"""
    def __init__(self, x: int, y: int, width: int, height: int, name: str):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
        
    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, Colors.OBSTACLE, 
                        (self.x, self.y, self.width, self.height), 
                        border_radius=5)
        pygame.draw.rect(screen, Colors.WALL, 
                        (self.x, self.y, self.width, self.height), 
                        width=2, border_radius=5)
        
        # Nom du meuble
        font = pygame.font.Font(None, 16)
        text = font.render(self.name, True, Colors.TEXT)
        text_rect = text.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
        screen.blit(text, text_rect)
    
    def collides_with_point(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

class Room:
    """Pièce avec niveau de saleté"""
    def __init__(self, name: str, x: int, y: int, width: int, height: int):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.dirt_level = DirtLevel.CLEAN
        self.dirt_particles = []
        self.center = (x + width // 2, y + height // 2)
        self.dirt_history = []  # Historique pour apprendre
        self.last_cleaned = 0
        
    def get_dirt_value(self) -> int:
        return self.dirt_level.value
    
    def get_cleaning_time(self) -> float:
        """Temps de nettoyage selon niveau"""
        return CLEANING_BASE_TIME * (1 + self.dirt_level.value)
    
    def make_dirty(self, level: DirtLevel = None):
        """Rend la pièce sale"""
        if level is None:
            # Augmente progressivement
            if self.dirt_level.value < 3:
                self.dirt_level = DirtLevel(self.dirt_level.value + 1)
        else:
            self.dirt_level = level
        
        self.dirt_history.append(pygame.time.get_ticks() / 1000)
        self._generate_particles()
    
    def _generate_particles(self):
        """Génère des particules de saleté"""
        self.dirt_particles = []
        num_particles = 10 + self.dirt_level.value * 10
        for _ in range(num_particles):
            px = random.randint(self.x + 10, self.x + self.width - 10)
            py = random.randint(self.y + 10, self.y + self.height - 10)
            size = random.uniform(2, 4 + self.dirt_level.value)
            self.dirt_particles.append((px, py, size))
    
    def clean(self, current_time: float):
        """Nettoie la pièce"""
        self.dirt_level = DirtLevel.CLEAN
        self.dirt_particles = []
        self.last_cleaned = current_time
    
    def get_color(self) -> Tuple[int, int, int]:
        """Couleur selon niveau de saleté"""
        colors = {
            DirtLevel.CLEAN: Colors.CLEAN,
            DirtLevel.DUSTY: Colors.DUSTY,
            DirtLevel.DIRTY: Colors.DIRTY,
            DirtLevel.VERY_DIRTY: Colors.VERY_DIRTY
        }
        return colors[self.dirt_level]
    
    def draw(self, screen: pygame.Surface):
        """Dessine la pièce"""
        # Fond
        color = self.get_color()
        for i in range(3):
            alpha = 40 + i * 15
            s = pygame.Surface((self.width - i*6, self.height - i*6), pygame.SRCALPHA)
            pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=10)
            screen.blit(s, (self.x + i*3, self.y + i*3))
        
        # Bordure
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height), 
                        width=3, border_radius=10)
        
        # Particules de saleté
        for px, py, size in self.dirt_particles:
            pygame.draw.circle(screen, (120, 53, 15), (int(px), int(py)), int(size))
        
        # Nom
        font = pygame.font.Font(None, 28)
        text = font.render(self.name, True, Colors.TEXT)
        screen.blit(text, (self.x + 10, self.y + 10))
        
        # Niveau de saleté
        level_names = ["PROPRE", "POUSSIÉREUX", "SALE", "TRÈS SALE"]
        level_font = pygame.font.Font(None, 20)
        level_text = level_font.render(level_names[self.dirt_level.value], True, Colors.TEXT)
        screen.blit(level_text, (self.x + 10, self.y + 40))

class ChargingStation:
    """Station de chargement"""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.width = 100
        self.height = 80
        self.center = (x + self.width // 2, y + self.height // 2)
        self.animation = 0
        
    def update(self, dt: float):
        self.animation = (self.animation + 100 * dt) % 360
        
    def draw(self, screen: pygame.Surface):
        # Base
        pygame.draw.rect(screen, Colors.STATION, 
                        (self.x, self.y, self.width, self.height), 
                        border_radius=8)
        
        # Bordure animée
        glow_alpha = int(50 + 30 * math.sin(math.radians(self.animation)))
        for i in range(3):
            # Créer une surface avec transparence pour l'effet de bordure
            border_surface = pygame.Surface((self.width + i*4, self.height + i*4), pygame.SRCALPHA)
            color = (*Colors.STATION, max(0, min(255, glow_alpha - i*15)))  # S'assurer que alpha est entre 0 et 255
            pygame.draw.rect(border_surface, color, 
                           (0, 0, self.width + i*4, self.height + i*4), 
                           width=2, border_radius=8)
            screen.blit(border_surface, (self.x - i*2, self.y - i*2))
        
        # Symboles
        font = pygame.font.Font(None, 35)
        bolt = font.render("⚡", True, (255, 215, 0))
        screen.blit(bolt, (self.x + 15, self.y + 15))
        
        trash = font.render("🗑️", True, (100, 200, 100))
        screen.blit(trash, (self.x + 55, self.y + 15))
        
        # Texte
        text_font = pygame.font.Font(None, 18)
        text = text_font.render("STATION", True, Colors.TEXT)
        screen.blit(text, (self.x + 20, self.y + 55))

class PathfindingAStar:
    """Pathfinding A* pour navigation optimale"""
    def __init__(self, environment):
        self.environment = environment
        self.grid_width = WIDTH // TILE_SIZE
        self.grid_height = HEIGHT // TILE_SIZE
        
    def is_walkable(self, x: int, y: int) -> bool:
        """Vérifie si une case est praticable"""
        # Hors limites
        if x < 0 or x >= self.grid_width or y < 0 or y >= self.grid_height:
            return False
        
        px, py = x * TILE_SIZE, y * TILE_SIZE
        
        # Vérifie collision avec obstacles
        for obstacle in self.environment.obstacles:
            if obstacle.collides_with_point(px, py):
                return False
        
        return True
    
    def heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Distance de Manhattan"""
        return abs(x1 - x2) + abs(y1 - y2)
    
    def get_neighbors(self, node: Node) -> List[Node]:
        """Obtient les voisins d'un noeud"""
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0), 
                     (1, 1), (-1, -1), (1, -1), (-1, 1)]  # 8 directions
        
        for dx, dy in directions:
            nx, ny = node.x + dx, node.y + dy
            if self.is_walkable(nx, ny):
                cost = 1.4 if abs(dx) + abs(dy) == 2 else 1  # Diagonale coûte plus
                neighbors.append((Node(nx, ny), cost))
        
        return neighbors
    
    def find_path(self, start_pos: Tuple[int, int], goal_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Trouve le chemin optimal avec A*"""
        start_x = int(start_pos[0] // TILE_SIZE)
        start_y = int(start_pos[1] // TILE_SIZE)
        goal_x = int(goal_pos[0] // TILE_SIZE)
        goal_y = int(goal_pos[1] // TILE_SIZE)
        
        start_node = Node(start_x, start_y, g=0)
        start_node.h = self.heuristic(start_x, start_y, goal_x, goal_y)
        goal_node = Node(goal_x, goal_y)
        
        open_set = [start_node]
        closed_set = set()
        nodes_dict = {(start_x, start_y): start_node}
        
        while open_set:
            current = heapq.heappop(open_set)
            
            if current.x == goal_x and current.y == goal_y:
                # Reconstruire le chemin
                path = []
                while current:
                    path.append((current.x * TILE_SIZE + TILE_SIZE//2, 
                               current.y * TILE_SIZE + TILE_SIZE//2))
                    current = current.parent
                return path[::-1]
            
            closed_set.add((current.x, current.y))
            
            for neighbor, cost in self.get_neighbors(current):
                if (neighbor.x, neighbor.y) in closed_set:
                    continue
                
                tentative_g = current.g + cost
                
                if (neighbor.x, neighbor.y) not in nodes_dict:
                    nodes_dict[(neighbor.x, neighbor.y)] = neighbor
                    neighbor.h = self.heuristic(neighbor.x, neighbor.y, goal_x, goal_y)
                else:
                    neighbor = nodes_dict[(neighbor.x, neighbor.y)]
                
                if tentative_g < neighbor.g:
                    neighbor.g = tentative_g
                    neighbor.parent = current
                    
                    if neighbor not in open_set:
                        heapq.heappush(open_set, neighbor)
        
        return []  # Pas de chemin trouvé

class VacuumAgent:
    """Agent aspirateur intelligent avec A*"""
    def __init__(self, start_pos: Tuple[int, int], pathfinder: PathfindingAStar):
        self.x, self.y = start_pos
        self.start_pos = start_pos
        self.target_x, self.target_y = start_pos
        self.state = AgentState.IDLE
        self.speed = 4
        self.size = 18
        self.angle = 0
        
        self.battery = MAX_BATTERY
        self.dirt_level = 0
        
        self.cleaning_progress = 0
        self.charging_progress = 0
        self.emptying_progress = 0
        
        self.current_room = None
        self.target_room = None
        self.particles: List[Particle] = []
        
        # Pathfinding
        self.pathfinder = pathfinder
        self.current_path = []
        self.path_index = 0
        
        # Mémoire
        self.rooms_memory = defaultdict(lambda: {"dirt_count": 0, "last_clean": 0})
        
        # Stats
        self.total_distance = 0
        self.total_cleanings = 0
        self.time_cleaning = 0
        
        # Mode manuel
        self.manual_mode = False
        
    def learn_room_pattern(self, room: Room):
        """Apprend les patterns de saleté"""
        self.rooms_memory[room.name]["dirt_count"] += 1
    
    def get_priority_room(self, dirty_rooms: List[Room]) -> Optional[Room]:
        """Choisit la pièce prioritaire"""
        if not dirty_rooms:
            return None
        
        # Priorise : niveau de saleté + fréquence
        best_room = max(dirty_rooms, key=lambda r: 
                       r.get_dirt_value() * 2 + self.rooms_memory[r.name]["dirt_count"] * 0.5)
        return best_room
    
    def needs_maintenance(self) -> bool:
        return self.battery < 25 or self.dirt_level >= MAX_DIRT_CAPACITY
    
    def move_to(self, target_pos: Tuple[int, int], target_room: Room = None):
        """Déplace l'agent vers une position via A*"""
        self.current_path = self.pathfinder.find_path((self.x, self.y), target_pos)
        self.path_index = 0
        self.target_room = target_room
        if self.current_path:
            self.state = AgentState.MOVING
    
    def update(self, dt: float) -> bool:
        """Met à jour l'agent"""
        self.angle = (self.angle + 3) % 360
        
        # Déplacement le long du chemin
        if self.state in [AgentState.MOVING, AgentState.RETURNING]:
            if self.current_path and self.path_index < len(self.current_path):
                target = self.current_path[self.path_index]
                dx = target[0] - self.x
                dy = target[1] - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist < self.speed:
                    self.x, self.y = target
                    self.path_index += 1
                    if self.path_index >= len(self.current_path):
                        return True
                else:
                    self.x += (dx / dist) * self.speed
                    self.y += (dy / dist) * self.speed
                    self.total_distance += self.speed * dt
                
                self.battery = max(0, self.battery - BATTERY_DRAIN_MOVE * dt)
        
        # Particules
        for particle in self.particles[:]:
            particle.x += particle.vx
            particle.y += particle.vy
            particle.life -= dt
            if particle.life <= 0:
                self.particles.remove(particle)
        
        return False
    
    def start_cleaning(self, room: Room):
        self.state = AgentState.CLEANING
        self.cleaning_progress = 0
        self.current_room = room
    
    def update_cleaning(self, dt: float, room: Room) -> bool:
        cleaning_time = room.get_cleaning_time()
        self.cleaning_progress += dt / cleaning_time
        
        drain = BATTERY_DRAIN_CLEAN_BASE * (1 + room.get_dirt_value() * 0.5)
        self.battery = max(0, self.battery - drain * dt)
        self.dirt_level = min(MAX_DIRT_CAPACITY, 
                             self.dirt_level + DIRT_PER_CLEAN * dt / cleaning_time)
        self.time_cleaning += dt
        
        # Particules d'aspiration
        if random.random() < 0.4:
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 6)
            color = [120, 53, 15] if random.random() < 0.7 else [200, 200, 200]
            self.particles.append(Particle(
                x=self.x, y=self.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=0.8, size=random.uniform(2, 5),
                color=tuple(color)
            ))
        
        return self.cleaning_progress >= 1.0
    
    def start_charging(self):
        self.state = AgentState.CHARGING
        self.charging_progress = 0
    
    def update_charging(self, dt: float) -> bool:
        self.battery = min(MAX_BATTERY, self.battery + CHARGING_RATE * dt)
        self.charging_progress = self.battery / MAX_BATTERY
        return self.battery >= MAX_BATTERY
    
    def start_emptying(self):
        self.state = AgentState.EMPTYING
        self.emptying_progress = 0
    
    def update_emptying(self, dt: float) -> bool:
        self.emptying_progress += dt / EMPTYING_TIME
        self.dirt_level = max(0, self.dirt_level - (MAX_DIRT_CAPACITY * dt / EMPTYING_TIME))
        return self.emptying_progress >= 1.0
    
    def return_to_station(self, station_pos: Tuple[int, int]):
        self.state = AgentState.RETURNING
        self.move_to(station_pos)
    
    def draw(self, screen: pygame.Surface):
        # Chemin A*
        if self.current_path and self.state in [AgentState.MOVING, AgentState.RETURNING]:
            for i in range(self.path_index, len(self.current_path) - 1):
                pygame.draw.line(screen, Colors.PATH, 
                               self.current_path[i], self.current_path[i+1], 3)
        
        # Lueur
        for i in range(3):
            radius = self.size + i * 8
            alpha = 40 - i * 12
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*Colors.ROBOT_GLOW, alpha), (radius, radius), radius)
            screen.blit(s, (self.x - radius, self.y - radius))
        
        # Corps
        pygame.draw.circle(screen, Colors.ROBOT, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(screen, Colors.ROBOT_GLOW, (int(self.x), int(self.y)), self.size, 3)
        
        # Direction
        end_x = self.x + math.cos(math.radians(self.angle)) * (self.size - 4)
        end_y = self.y + math.sin(math.radians(self.angle)) * (self.size - 4)
        pygame.draw.line(screen, Colors.TEXT, (self.x, self.y), (end_x, end_y), 2)
        
        # LED clignotante
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            led_x = self.x + math.cos(math.radians(self.angle + 90)) * 8
            led_y = self.y + math.sin(math.radians(self.angle + 90)) * 8
            pygame.draw.circle(screen, (255, 0, 0), (int(led_x), int(led_y)), 3)
        
        # Particules
        for particle in self.particles:
            alpha = int(particle.life * 255)
            s = pygame.Surface((particle.size*2, particle.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*particle.color, alpha), 
                             (particle.size, particle.size), particle.size)
            screen.blit(s, (particle.x - particle.size, particle.y - particle.size))
        
        # Barres de progression
        if self.state == AgentState.CLEANING:
            self._draw_progress_bar(screen, Colors.CLEAN)
        elif self.state == AgentState.CHARGING:
            self._draw_progress_bar(screen, (255, 215, 0))
        elif self.state == AgentState.EMPTYING:
            self._draw_progress_bar(screen, (100, 200, 100))
    
    def _draw_progress_bar(self, screen, color):
        bar_w, bar_h = 50, 6
        bar_x = self.x - bar_w // 2
        bar_y = self.y + self.size + 12
        
        pygame.draw.rect(screen, Colors.PANEL, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        
        progress = self.cleaning_progress if self.state == AgentState.CLEANING else \
                  (self.charging_progress if self.state == AgentState.CHARGING else self.emptying_progress)
        
        fill_w = int(bar_w * progress)
        pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

class Environment:
    """Environnement avec pièces et obstacles"""
    def __init__(self):
        # Définition des pièces
        margin = 50
        self.rooms = [
            Room("Salon", margin, margin, 300, 250),
            Room("Cuisine", margin + 320, margin, 280, 250),
            Room("Couloir", margin, margin + 270, 600, 100),
            Room("Chambre A", margin, margin + 390, 280, 200),
            Room("Chambre B", margin + 320, margin + 390, 280, 200)
        ]
        
        # Obstacles (meubles)
        self.obstacles = [
            Obstacle(80, 100, 80, 60, "Canapé"),
            Obstacle(200, 180, 60, 60, "Table"),
            Obstacle(380, 100, 100, 80, "Îlot"),
            Obstacle(100, 480, 60, 80, "Lit"),
            Obstacle(380, 500, 80, 60, "Bureau")
        ]
        
        # Station
        self.station = ChargingStation(margin + 250, margin + 300)
        
        # Pathfinding
        self.pathfinder = PathfindingAStar(self)
        
        # Agent
        self.agent = VacuumAgent(self.station.center, self.pathfinder)
        
        # Timing
        self.last_dirt_time = 0
        self.dirt_interval = random.uniform(8, 15)
        
        # Saletés initiales
        for room in random.sample(self.rooms, 3):
            room.make_dirty(DirtLevel(random.randint(1, 2)))
    
    def update_dirt(self, elapsed_time: float):
        if elapsed_time - self.last_dirt_time >= self.dirt_interval:
            # Salit une pièce aléatoire
            room = random.choice([r for r in self.rooms if r.dirt_level.value < 3])
            room.make_dirty()
            print(f"🗑️ {room.name} → {room.dirt_level.name}")
            
            self.last_dirt_time = elapsed_time
            self.dirt_interval = random.uniform(8, 15)
    
    def get_dirty_rooms(self) -> List[Room]:
        return [r for r in self.rooms if r.dirt_level != DirtLevel.CLEAN]
    
    def draw(self, screen: pygame.Surface):
        for room in self.rooms:
            room.draw(screen)
        for obstacle in self.obstacles:
            obstacle.draw(screen)
        self.station.draw(screen)
        self.agent.draw(screen)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("🤖 Aspirateur Autonome Intelligent A*")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.environment = Environment()
        self.elapsed_time = 0
        self.cycle_timer = 0
        self.current_action = "Initialisation..."
        
        self.fsm_state = "waiting"
        
        self.font_title = pygame.font.Font(None, 32)
        self.font_stats = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
    
    def draw_hud(self):
        """HUD avec statistiques"""
        hud_x = WIDTH - 350
        hud_y = 20
        hud_w = 330
        hud_h = HEIGHT - 40
        
        # Panneau
        s = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        pygame.draw.rect(s, (*Colors.PANEL, 240), s.get_rect(), border_radius=15)
        self.screen.blit(s, (hud_x, hud_y))
        pygame.draw.rect(self.screen, Colors.PANEL_ACCENT, 
                        (hud_x, hud_y, hud_w, hud_h), width=2, border_radius=15)
        
        y_offset = hud_y + 15
        
        # Titre
        title = self.font_title.render("📊 STATISTIQUES", True, Colors.TEXT)
        self.screen.blit(title, (hud_x + 20, y_offset))
        y_offset += 45
        
        agent = self.environment.agent
        
        # Batterie
        battery_pct = int(agent.battery)
        bat_color = Colors.CLEAN if battery_pct > 50 else (Colors.DUSTY if battery_pct > 20 else Colors.VERY_DIRTY)
        bat_text = self.font_stats.render(f"🔋 Batterie: {battery_pct}%", True, bat_color)
        self.screen.blit(bat_text, (hud_x + 20, y_offset))
        
        # Barre batterie
        self._draw_bar(hud_x + 20, y_offset + 25, 290, 15, battery_pct / 100, bat_color)
        y_offset += 55
        
        # Réservoir
        dirt_pct = int(agent.dirt_level)
        dirt_color = Colors.CLEAN if dirt_pct < 70 else (Colors.DUSTY if dirt_pct < 100 else Colors.VERY_DIRTY)
        dirt_text = self.font_stats.render(f"🗑️ Réservoir: {dirt_pct}%", True, dirt_color)
        self.screen.blit(dirt_text, (hud_x + 20, y_offset))
        
        # Barre réservoir
        self._draw_bar(hud_x + 20, y_offset + 25, 290, 15, dirt_pct / 100, dirt_color)
        y_offset += 60
        
        # Séparateur
        pygame.draw.line(self.screen, Colors.PANEL_ACCENT, 
                        (hud_x + 20, y_offset), (hud_x + hud_w - 20, y_offset), 2)
        y_offset += 15
        
        # État actuel
        state_text = self.font_stats.render("🎯 État:", True, Colors.TEXT)
        self.screen.blit(state_text, (hud_x + 20, y_offset))
        y_offset += 25
        
        action = self.font_small.render(self.current_action, True, Colors.ROBOT_GLOW)
        self.screen.blit(action, (hud_x + 25, y_offset))
        y_offset += 30
        
        # Pièce actuelle
        current_room = agent.target_room.name if agent.target_room else "Station"
        room_text = self.font_small.render(f"📍 Cible: {current_room}", True, Colors.TEXT)
        self.screen.blit(room_text, (hud_x + 25, y_offset))
        y_offset += 35
        
        # Séparateur
        pygame.draw.line(self.screen, Colors.PANEL_ACCENT, 
                        (hud_x + 20, y_offset), (hud_x + hud_w - 20, y_offset), 2)
        y_offset += 15
        
        # État des pièces
        rooms_title = self.font_stats.render("🏠 Pièces:", True, Colors.TEXT)
        self.screen.blit(rooms_title, (hud_x + 20, y_offset))
        y_offset += 30
        
        for room in self.environment.rooms:
            level_names = ["✓", "~", "!", "!!!"]
            level_colors = [Colors.CLEAN, Colors.DUSTY, Colors.DIRTY, Colors.VERY_DIRTY]
            
            name_text = self.font_small.render(f"{room.name}:", True, Colors.TEXT)
            self.screen.blit(name_text, (hud_x + 25, y_offset))
            
            status = self.font_small.render(level_names[room.dirt_level.value], True, level_colors[room.dirt_level.value])
            self.screen.blit(status, (hud_x + 240, y_offset))
            
            # Fréquence
            freq = agent.rooms_memory[room.name]["dirt_count"]
            if freq > 0:
                freq_text = self.font_small.render(f"x{freq}", True, (150, 150, 150))
                self.screen.blit(freq_text, (hud_x + 270, y_offset))
            
            y_offset += 25
        
        y_offset += 10
        
        # Séparateur
        pygame.draw.line(self.screen, Colors.PANEL_ACCENT, 
                        (hud_x + 20, y_offset), (hud_x + hud_w - 20, y_offset), 2)
        y_offset += 15
        
        # Performance
        perf_title = self.font_stats.render("📈 Performance:", True, Colors.TEXT)
        self.screen.blit(perf_title, (hud_x + 20, y_offset))
        y_offset += 30
        
        # Distance
        dist_m = agent.total_distance / 100
        dist_text = self.font_small.render(f"Distance: {dist_m:.1f}m", True, Colors.TEXT)
        self.screen.blit(dist_text, (hud_x + 25, y_offset))
        y_offset += 25
        
        # Nettoyages
        clean_text = self.font_small.render(f"Nettoyages: {agent.total_cleanings}", True, Colors.TEXT)
        self.screen.blit(clean_text, (hud_x + 25, y_offset))
        y_offset += 25
        
        # Temps de nettoyage
        clean_time = int(agent.time_cleaning)
        time_text = self.font_small.render(f"Temps nettoyage: {clean_time}s", True, Colors.TEXT)
        self.screen.blit(time_text, (hud_x + 25, y_offset))
        y_offset += 25
        
        # Efficacité
        total_rooms = len(self.environment.rooms)
        clean_rooms = sum(1 for r in self.environment.rooms if r.dirt_level == DirtLevel.CLEAN)
        efficiency = (clean_rooms / total_rooms) * 100
        eff_text = self.font_small.render(f"Propreté: {efficiency:.0f}%", True, Colors.CLEAN if efficiency > 70 else Colors.DUSTY)
        self.screen.blit(eff_text, (hud_x + 25, y_offset))
        y_offset += 35
        
        # Séparateur
        pygame.draw.line(self.screen, Colors.PANEL_ACCENT, 
                        (hud_x + 20, y_offset), (hud_x + hud_w - 20, y_offset), 2)
        y_offset += 15
        
        # Temps
        minutes = int(self.elapsed_time // 60)
        seconds = int(self.elapsed_time % 60)
        time_text = self.font_small.render(f"⏱️ Temps écoulé: {minutes:02d}:{seconds:02d}", True, Colors.TEXT)
        self.screen.blit(time_text, (hud_x + 25, y_offset))
        y_offset += 25
        
        # Prochain cycle
        next_cycle = CYCLE_DURATION - (self.cycle_timer % CYCLE_DURATION)
        cycle_text = self.font_small.render(f"🔄 Prochain cycle: {int(next_cycle)}s", True, Colors.DUSTY)
        self.screen.blit(cycle_text, (hud_x + 25, y_offset))
        y_offset += 30
        
        # Mode manuel
        if agent.manual_mode:
            mode_text = self.font_small.render("🎮 MODE MANUEL", True, Colors.VERY_DIRTY)
            self.screen.blit(mode_text, (hud_x + 25, y_offset))
        else:
            mode_text = self.font_small.render("🤖 MODE AUTO", True, Colors.CLEAN)
            self.screen.blit(mode_text, (hud_x + 25, y_offset))
        
        # Contrôles
        y_offset = hud_y + hud_h - 80
        pygame.draw.line(self.screen, Colors.PANEL_ACCENT, 
                        (hud_x + 20, y_offset), (hud_x + hud_w - 20, y_offset), 2)
        y_offset += 10
        
        controls_text = self.font_small.render("Contrôles:", True, Colors.TEXT)
        self.screen.blit(controls_text, (hud_x + 20, y_offset))
        y_offset += 20
        
        help1 = self.font_small.render("M: Mode manuel", True, (150, 150, 150))
        self.screen.blit(help1, (hud_x + 25, y_offset))
        y_offset += 18
        
        help2 = self.font_small.render("Flèches: Déplacer", True, (150, 150, 150))
        self.screen.blit(help2, (hud_x + 25, y_offset))
        y_offset += 18
        
        help3 = self.font_small.render("Espace: Nettoyer", True, (150, 150, 150))
        self.screen.blit(help3, (hud_x + 25, y_offset))
    
    def _draw_bar(self, x, y, width, height, progress, color):
        """Dessine une barre de progression"""
        # Fond
        pygame.draw.rect(self.screen, Colors.PANEL_ACCENT, 
                        (x, y, width, height), border_radius=5)
        # Remplissage
        fill_width = int(width * progress)
        if fill_width > 0:
            pygame.draw.rect(self.screen, color, 
                           (x, y, fill_width, height), border_radius=5)
        # Bordure
        pygame.draw.rect(self.screen, Colors.TEXT, 
                        (x, y, width, height), width=1, border_radius=5)
    
    def handle_manual_control(self, keys):
        """Gestion du mode manuel"""
        agent = self.environment.agent
        if not agent.manual_mode:
            return
        
        speed = 3
        moved = False
        
        if keys[pygame.K_LEFT]:
            agent.x -= speed
            moved = True
        if keys[pygame.K_RIGHT]:
            agent.x += speed
            moved = True
        if keys[pygame.K_UP]:
            agent.y -= speed
            moved = True
        if keys[pygame.K_DOWN]:
            agent.y += speed
            moved = True
        
        if moved:
            agent.battery = max(0, agent.battery - BATTERY_DRAIN_MOVE * (1/FPS))
            agent.total_distance += speed * (1/FPS)
        
        # Nettoyage manuel
        if keys[pygame.K_SPACE]:
            for room in self.environment.rooms:
                if (room.x < agent.x < room.x + room.width and 
                    room.y < agent.y < room.y + room.height):
                    if agent.state != AgentState.CLEANING:
                        agent.start_cleaning(room)
                        self.current_action = f"Nettoyage manuel: {room.name}"
                    break
    
    def run_fsm(self):
        """Automate à états finis"""
        agent = self.environment.agent
        station = self.environment.station
        
        if agent.manual_mode:
            return
        
        # Priorité: maintenance
        if self.fsm_state == "waiting" and agent.needs_maintenance():
            self.current_action = "⚠️ Maintenance → Station"
            agent.return_to_station(station.center)
            self.fsm_state = "returning"
            return
        
        if self.fsm_state == "waiting":
            dirty_rooms = self.environment.get_dirty_rooms()
            if dirty_rooms:
                target = agent.get_priority_room(dirty_rooms)
                agent.learn_room_pattern(target)
                self.current_action = f"Cible: {target.name} (niveau {target.dirt_level.value})"
                agent.move_to(target.center, target)
                self.fsm_state = "moving"
            else:
                self.current_action = "Surveillance → Tout propre ✓"
        
        elif self.fsm_state == "moving":
            if agent.update(1/FPS):
                self.current_action = f"Nettoyage de {agent.target_room.name}..."
                agent.start_cleaning(agent.target_room)
                self.fsm_state = "cleaning"
        
        elif self.fsm_state == "cleaning":
            if agent.update_cleaning(1/FPS, agent.target_room):
                agent.target_room.clean(self.elapsed_time)
                agent.total_cleanings += 1
                
                if agent.needs_maintenance():
                    self.current_action = "Maintenance → Station"
                    agent.return_to_station(station.center)
                    self.fsm_state = "returning"
                else:
                    dirty_rooms = self.environment.get_dirty_rooms()
                    if dirty_rooms:
                        target = agent.get_priority_room(dirty_rooms)
                        agent.learn_room_pattern(target)
                        self.current_action = f"Suivant: {target.name}"
                        agent.move_to(target.center, target)
                        self.fsm_state = "moving"
                    else:
                        self.current_action = "Terminé → Retour station"
                        agent.return_to_station(station.center)
                        self.fsm_state = "returning"
        
        elif self.fsm_state == "returning":
            if agent.update(1/FPS):
                if agent.dirt_level >= MAX_DIRT_CAPACITY * 0.8:
                    self.current_action = "🗑️ Vidage..."
                    agent.start_emptying()
                    self.fsm_state = "emptying"
                elif agent.battery < 90:
                    self.current_action = "🔋 Recharge..."
                    agent.start_charging()
                    self.fsm_state = "charging"
                else:
                    self.current_action = "Station → En attente"
                    agent.state = AgentState.IDLE
                    self.fsm_state = "waiting"
        
        elif self.fsm_state == "emptying":
            if agent.update_emptying(1/FPS):
                if agent.battery < 90:
                    self.current_action = "🔋 Recharge..."
                    agent.start_charging()
                    self.fsm_state = "charging"
                else:
                    self.current_action = "Maintenance terminée ✓"
                    agent.state = AgentState.IDLE
                    self.fsm_state = "waiting"
        
        elif self.fsm_state == "charging":
            if agent.update_charging(1/FPS):
                self.current_action = "Recharge terminée ✓"
                agent.state = AgentState.IDLE
                self.fsm_state = "waiting"
    
    def run(self):
        """Boucle principale"""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.elapsed_time += dt
            self.cycle_timer += dt
            
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_m:
                        # Toggle mode manuel
                        self.environment.agent.manual_mode = not self.environment.agent.manual_mode
                        if self.environment.agent.manual_mode:
                            self.current_action = "🎮 Mode manuel activé"
                            self.fsm_state = "manual"
                        else:
                            self.current_action = "🤖 Mode automatique"
                            self.fsm_state = "waiting"
            
            # Contrôles manuels
            keys = pygame.key.get_pressed()
            self.handle_manual_control(keys)
            
            # Génération de saleté
            self.environment.update_dirt(self.elapsed_time)
            
            # Station
            self.environment.station.update(dt)
            
            # Cycle automatique
            if self.cycle_timer >= CYCLE_DURATION:
                self.cycle_timer = 0
                if self.fsm_state == "waiting":
                    self.current_action = "Cycle: Analyse..."
            
            # FSM
            self.run_fsm()
            
            # Agent updates (particules)
            if self.environment.agent.state not in [AgentState.CLEANING, AgentState.MOVING, AgentState.RETURNING]:
                self.environment.agent.update(dt)
            
            # Affichage
            self.screen.fill(Colors.BG)
            self.environment.draw(self.screen)
            self.draw_hud()
            
            pygame.display.flip()
        
        pygame.quit()

# Point d'entrée
if __name__ == "__main__":
    game = Game()
    game.run()