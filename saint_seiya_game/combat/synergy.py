"""
Módulo Synergy - Sistema de sinergias entre personajes del mismo equipo.
Las sinergias otorgan bonificaciones estadísticas al equipo al inicio del combate.
"""


# Definición de sinergias disponibles
SYNERGY_DEFINITIONS = {
    "bronze_saint_full": {
        "name": "Los 5 Santos de Bronce",
        "description": "Cuando los 5 santos de bronce están juntos, su Cosmo alcanza su máximo potencial.",
        "required_tags": ["bronze_saint"],
        "required_count": 5,
        "bonuses": {
            "atk": 0.10,       # +10% ATK a todo el equipo
            "crit_rate": 5,    # +5% crit rate
            "cosmo_bonus": 20, # Empiezan con 20 de Cosmo
        }
    },
    "saints_trio": {
        "name": "Dúo de Santos",
        "description": "Dos o más santos juntos se potencian mutuamente.",
        "required_tags": ["bronze_saint"],
        "required_count": 2,
        "bonuses": {
            "atk": 0.05,
        }
    },
    "offensive_trinity": {
        "name": "Trinidad Ofensiva",
        "description": "Seiya, Ikki y un tercer atacante forman la trinidad del poder.",
        "required_tags": ["offensive"],
        "required_count": 3,
        "bonuses": {
            "atk": 0.08,
            "crit_dmg": 10,
        }
    },
    "tank_line": {
        "name": "Muro Inquebrantable",
        "description": "Tener un tank mejora la resistencia de todos.",
        "required_tags": ["tank"],
        "required_count": 1,
        "bonuses": {
            "def": 0.08,
        }
    },
    "control_mastery": {
        "name": "Control Total",
        "description": "Maestros del control que aumentan las chances de efectos de estado.",
        "required_tags": ["control"],
        "required_count": 2,
        "bonuses": {
            "status_chance_bonus": 10,  # +10% chance a todos los efectos
        }
    },
    "support_boost": {
        "name": "Apoyo del Equipo",
        "description": "El soporte mejora la supervivencia del equipo.",
        "required_tags": ["support"],
        "required_count": 1,
        "bonuses": {
            "hp": 0.05,
        }
    },
}


def calculate_synergies(team: list) -> tuple:
    """
    Calcula las sinergias activas para un equipo.

    Args:
        team: Lista de Fighter del equipo

    Returns:
        (active_synergies: list, total_bonuses: dict)
    """
    # Contar tags en el equipo
    tag_counts = {}
    for fighter in team:
        for tag in fighter.synergy_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    active_synergies = []
    total_bonuses = {
        'atk': 0.0,
        'def': 0.0,
        'hp': 0.0,
        'crit_rate': 0,
        'crit_dmg': 0,
        'cosmo_bonus': 0,
        'status_chance_bonus': 0,
    }

    # Priorizar la sinergia más completa
    checked = set()

    for syn_id, syn in SYNERGY_DEFINITIONS.items():
        required_tags = syn['required_tags']
        required_count = syn['required_count']

        # Verificar si se cumple la sinergia
        meets_requirement = all(
            tag_counts.get(tag, 0) >= required_count
            for tag in required_tags
        )

        if meets_requirement and syn_id not in checked:
            # Evitar sinergias redundantes (e.g., no activar "dúo" si hay "full team")
            # La sinergia full team es prioritaria
            if syn_id == 'saints_trio' and 'bronze_saint_full' in [
                s['id'] for s in active_synergies
            ]:
                continue

            active_synergies.append({
                'id': syn_id,
                'name': syn['name'],
                'description': syn['description'],
                'bonuses': syn['bonuses'],
            })
            checked.add(syn_id)

            for stat, val in syn['bonuses'].items():
                if stat in total_bonuses:
                    total_bonuses[stat] += val

    return active_synergies, total_bonuses


def apply_synergy_bonuses(team: list, bonuses: dict):
    """Aplica los bonos de sinergia a todos los miembros del equipo."""
    for fighter in team:
        # ATK bonus
        if bonuses.get('atk'):
            fighter.base_atk = int(fighter.base_atk * (1 + bonuses['atk']))

        # DEF bonus
        if bonuses.get('def'):
            fighter.base_def = int(fighter.base_def * (1 + bonuses['def']))

        # HP bonus
        if bonuses.get('hp'):
            bonus_hp = int(fighter.max_hp * bonuses['hp'])
            fighter.max_hp += bonus_hp
            fighter.current_hp += bonus_hp

        # Crit bonuses
        if bonuses.get('crit_rate'):
            fighter.crit_rate = min(95, fighter.crit_rate + bonuses['crit_rate'])

        if bonuses.get('crit_dmg'):
            fighter.crit_dmg += bonuses['crit_dmg']

        # Cosmo inicial (solo heroes)
        from entities import Hero
        if isinstance(fighter, Hero) and bonuses.get('cosmo_bonus'):
            fighter.cosmo = bonuses['cosmo_bonus']
