#  Aspirateur Autonome Intelligent 

Un simulateur d'aspirateur intelligent avec pathfinding A* qui gère autonomiquement le nettoyage d'une maison avec gestion de batterie, réservoir et apprentissage des patterns de saleté.

## Fonctionnalités

### Navigation Intelligente
- **Algorithme *** pour trouver le chemin optimal
- Navigation autour des obstacles (meubles)
- Visualisation du chemin en temps réel
- 8 directions de mouvement (4 directions + diagonales)

### Intelligence Artificielle
- **Automate à états finis** pour la gestion des tâches
- **Apprentissage des patterns** de saleté par pièce
- Système de priorité basé sur:
  - Niveau de saleté (PROPRE → POUSSIÉREUX → SALE → TRÈS SALE)
  - Fréquence d'apparition de la saleté
- Optimisation des trajets

### Gestion des Ressources
- **Batterie**: Décharge progressive pendant le mouvement et nettoyage
- **Réservoir**: Capacité limitée (100 unités)
- **États de maintenance**:
  - Recharge (20% par seconde)
  - Vidage (2 secondes)
  - Nettoyage (temps variable selon saleté)

### Environnement Dynamique
- 5 pièces avec niveaux de saleté variables:
  - Salon
  - Cuisine
  - Couloir
  - Chambre A
  - Chambre B
- 5 obstacles (meubles) à contourner
- 1 station de recharge/vidage
- Génération aléatoire de saleté

### Statistiques en Temps Réel
- État de la batterie et réservoir
- Distance parcourue
- Nombre de nettoyages effectués
- Temps de nettoyage total
- Taux de propreté global
- Fréquence de saleté par pièce

### Deux Modes de Fonctionnement

#### Mode Automatique (défaut)
L'aspirateur fonctionne entièrement seul avec la FSM (automate à états finis)

#### Mode Manuel
Contrôlez manuellement l'aspirateur avec:
- **Flèches** : Déplacer l'aspirateur
- **Espace** : Déclencher le nettoyage

## Installation

### Prérequis
- Python 3.8+
- Pygame

### Étapes

1. Clonez le repository:
```bash
git clone <url-du-repo>
cd aspirateur
```

2. Installez les dépendances:
```bash
pip install -r requirements.txt
```

3. Lancez le programme:
```bash
python aspirateurv2.py
```

## Contrôles

| Touche | Action |
|--------|--------|
| **M** | Basculer entre mode automatique/manuel |
| **↑** | Monter (mode manuel) |
| **↓** | Descendre (mode manuel) |
| **←** | Aller à gauche (mode manuel) |
| **→** | Aller à droite (mode manuel) |
| **Espace** | Déclencher nettoyage (mode manuel) |
| **Échap** | Quitter |

## Architecture

### Classes Principales

#### `VacuumAgent`
Agent principal avec:
- Gestion de la batterie et du réservoir
- Pathfinding A*
- Mémoire d'apprentissage
- Statut et position

#### `Environment`
Gère:
- Les 5 pièces et leurs niveaux de saleté
- Les 5 obstacles
- La station de recharge
- L'agent aspirateur
- La génération aléatoire de saleté

#### `PathfindingAStar`
Calcule les chemins optimaux:
- Grille de tuiles (20x20 pixels)
- Évite les obstacles
- Heuristique de Manhattan
- 8 directions de déplacement

#### `Room`
Représente une pièce avec:
- Niveau de saleté
- Particules visuelles
- Historique de nettoyage
- Apprentissage

#### `ChargingStation`
Station avec:
- Animation de charge
- Recharge et vidage

#### `Game`
Boucle principale avec:
- FSM (automate à états finis)
- Gestion des événements
- Rendu HUD
- Timing et FPS

### États de la FSM

```
waiting → moving → cleaning → [maintenance] → returning → [emptying/charging] → waiting
```

- **waiting**: En attente de commande
- **moving**: Navigation vers la pièce cible
- **cleaning**: Nettoyage en cours
- **returning**: Retour à la station
- **emptying**: Vidage du réservoir
- **charging**: Recharge de la batterie

## Paramètres Configurable

```python
# Timing
CYCLE_DURATION = 120        # 2 minutes
CLEANING_BASE_TIME = 2      # Base en secondes
CHARGING_RATE = 20          # % par seconde

# Batterie et ressources
MAX_BATTERY = 100
BATTERY_DRAIN_MOVE = 0.3    # Par seconde
BATTERY_DRAIN_CLEAN_BASE = 1.5  # Par seconde
MAX_DIRT_CAPACITY = 100
DIRT_PER_CLEAN = 25

# Résolution et FPS
WIDTH, HEIGHT = 1300, 800
FPS = 60
TILE_SIZE = 20  # Grille pour pathfinding
```

## Système de Couleurs

- **Vert** (#22C55E): Propre
- **Jaune** (#FBbf24): Poussiéreux
- **Orange** (#F97316): Sale
- **Rouge** (#EF4444): Très sale
- **Bleu** (#3B82F6): Robot
- **Violet** (#9333EA): Station

## Métriques de Performance

L'HUD affiche:
- **Batterie**: En % avec code couleur
- **Réservoir**: En % avec code couleur
- **État actuel**: Action en cours
- **Cible**: Pièce visée
- **État des pièces**: Avec fréquence de saleté
- **Performance**: Distance, nettoyages, temps
- **Propreté**: % de pièces propres

## Améliorations Futures

- [ ] Plusieurs agents aspirateurs
- [ ] Génération procédurale de pièces
- [ ] Sauvegarde/Chargement de l'état
- [ ] Réseau de neurones pour apprentissage
- [ ] Système de réparation/maintenance
- [ ] Patterns de saleté plus complexes
- [ ] Simulation de durée de batterie réaliste

## Notes Techniques

- **Pygame**: Rendu graphique
- **Heapq**: File de priorité pour A*
- **Dataclasses**: Structure de données pour Node et Particle
- **Enum**: États et niveaux de saleté
- **Defaultdict**: Mémoire d'apprentissage

## License

Ce projet est un projet pédagogique pour l'IA et les systèmes multi-agents.

## Auteur

Créé comme projet d'apprentissage IA 

---

**Bon nettoyage!**
