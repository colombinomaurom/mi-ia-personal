"""
Módulo Effects - Definición y aplicación de todos los efectos de estado.
Gestiona aplicación, icono, descripción y comportamiento de cada efecto.
"""

# Definición de efectos con sus propiedades
EFFECT_DEFINITIONS = {
    "stun": {
        "name": "Aturdido",
        "icon": "⭐",
        "color": "#FFD700",
        "description": "No puede actuar este turno.",
        "prevents_action": True,
        "is_dot": False,
    },
    "freeze": {
        "name": "Congelado",
        "icon": "🧊",
        "color": "#00BFFF",
        "description": "Congelado, no puede actuar. Vulnerable a daño de hielo x2.",
        "prevents_action": True,
        "is_dot": False,
    },
    "petrify": {
        "name": "Petrificado",
        "icon": "🗿",
        "color": "#808080",
        "description": "Convertido en piedra, no puede actuar.",
        "prevents_action": True,
        "is_dot": False,
    },
    "sleep": {
        "name": "Dormido",
        "icon": "💤",
        "color": "#9370DB",
        "description": "Dormido. Se despierta al recibir daño.",
        "prevents_action": True,
        "breaks_on_damage": True,
        "is_dot": False,
    },
    "bind": {
        "name": "Inmovilizado",
        "icon": "⛓️",
        "color": "#8B4513",
        "description": "Las cadenas lo inmovilizan este turno.",
        "prevents_action": True,
        "is_dot": False,
    },
    "confusion": {
        "name": "Confundido",
        "icon": "🌀",
        "color": "#FF69B4",
        "description": "Atacará a un aliado aleatorio en lugar del enemigo.",
        "prevents_action": False,
        "causes_friendly_fire": True,
        "is_dot": False,
    },
    "silence": {
        "name": "Silenciado",
        "icon": "🔇",
        "color": "#696969",
        "description": "No puede usar habilidades que cuestan MP.",
        "prevents_action": False,
        "prevents_mp_skills": True,
        "is_dot": False,
    },
    "burn": {
        "name": "Quemado",
        "icon": "🔥",
        "color": "#FF4500",
        "description": "Pierde 4% de HP máximo por turno.",
        "prevents_action": False,
        "is_dot": True,
        "dot_pct": 0.04,
    },
    "bleed": {
        "name": "Sangrando",
        "icon": "🩸",
        "color": "#DC143C",
        "description": "Pierde 3.5% de HP máximo por turno.",
        "prevents_action": False,
        "is_dot": True,
        "dot_pct": 0.035,
    },
    "shield": {
        "name": "Escudo",
        "icon": "🛡️",
        "color": "#4169E1",
        "description": "Absorbe daño hasta el límite del escudo.",
        "prevents_action": False,
        "is_dot": False,
    },
    "atk_up": {
        "name": "ATK Aumentado",
        "icon": "⬆️",
        "color": "#FF8C00",
        "description": "Ataque aumentado.",
        "prevents_action": False,
        "is_dot": False,
    },
    "atk_down": {
        "name": "ATK Reducido",
        "icon": "⬇️",
        "color": "#FF8C00",
        "description": "Ataque reducido.",
        "prevents_action": False,
        "is_dot": False,
    },
    "def_up": {
        "name": "DEF Aumentada",
        "icon": "🔼",
        "color": "#4169E1",
        "description": "Defensa aumentada.",
        "prevents_action": False,
        "is_dot": False,
    },
    "def_down": {
        "name": "DEF Reducida",
        "icon": "🔽",
        "color": "#4169E1",
        "description": "Defensa reducida.",
        "prevents_action": False,
        "is_dot": False,
    },
    "spd_down": {
        "name": "Velocidad Reducida",
        "icon": "🐌",
        "color": "#9ACD32",
        "description": "Velocidad reducida.",
        "prevents_action": False,
        "is_dot": False,
    },
    "crit_up": {
        "name": "Crítico Aumentado",
        "icon": "💢",
        "color": "#FF1493",
        "description": "Probabilidad de crítico aumentada.",
        "prevents_action": False,
        "is_dot": False,
    },
    "mp_drain": {
        "name": "Drenaje de MP",
        "icon": "💜",
        "color": "#8B008B",
        "description": "Pierdes MP cada turno.",
        "prevents_action": False,
        "is_dot": False,
    },
    "death_mark": {
        "name": "Marca de Muerte",
        "icon": "💀",
        "color": "#000000",
        "description": "El próximo golpe que recibas causará el doble de daño.",
        "prevents_action": False,
        "is_dot": False,
    },
    "dodge_up": {
        "name": "Esquiva Aumentada",
        "icon": "💨",
        "color": "#87CEEB",
        "description": "Mayor probabilidad de esquivar ataques.",
        "prevents_action": False,
        "is_dot": False,
    },
}


def create_effect(effect_type: str, duration: int, value: float = 0.0,
                  source: str = None) -> dict:
    """
    Crea un diccionario de efecto de estado listo para aplicar.

    Args:
        effect_type: Tipo del efecto (ver EFFECT_DEFINITIONS)
        duration: Duración en turnos
        value: Valor del modificador (para buffs/debuffs)
        source: Nombre del lanzador (para el log)
    """
    defn = EFFECT_DEFINITIONS.get(effect_type, {})
    effect = {
        'type': effect_type,
        'duration': duration,
        'value': value,
        'source': source,
        'name': defn.get('name', effect_type),
        'icon': defn.get('icon', '❓'),
        'color': defn.get('color', '#FFFFFF'),
        'dot_pct': defn.get('dot_pct', 0),
    }
    return effect


def get_effect_info(effect_type: str) -> dict:
    """Retorna información de un tipo de efecto."""
    return EFFECT_DEFINITIONS.get(effect_type, {
        'name': effect_type,
        'icon': '❓',
        'color': '#FFFFFF',
        'description': 'Efecto desconocido.',
        'prevents_action': False,
        'is_dot': False,
    })


def apply_status_effect(target, skill: dict, caster, random_module) -> list:
    """
    Intenta aplicar el efecto de estado de una habilidad al objetivo.
    Retorna lista de eventos generados.
    """
    events = []
    effect_type = skill.get('status_effect')
    if not effect_type:
        return events

    chance = skill.get('status_chance', 0)

    # El objetivo del buff/debuff puede ser 'self' (caster) o 'all_allies'
    status_target = skill.get('status_target', 'target')

    if status_target == 'self':
        actual_targets = [caster]
    elif status_target == 'all_allies':
        # Esto se resuelve en executor.py
        actual_targets = [caster]
    else:
        actual_targets = [target]

    for t in actual_targets:
        roll = random_module.randint(1, 100)
        if roll <= chance:
            duration = skill.get('status_duration', 1)
            value = skill.get('status_value', 0.0)

            # Escudo usa porcentaje del HP máximo
            if effect_type == 'shield':
                shield_pct = skill.get('shield_pct', 0.25)
                value = int(t.max_hp * shield_pct)

            effect = create_effect(
                effect_type=effect_type,
                duration=duration,
                value=value,
                source=caster.name
            )
            t.add_status_effect(effect)

            defn = EFFECT_DEFINITIONS.get(effect_type, {})
            events.append({
                'type': 'status_applied',
                'effect': effect_type,
                'target': t.name,
                'target_id': t.id,
                'duration': duration,
                'icon': defn.get('icon', '❓'),
                'name': defn.get('name', effect_type),
                'value': value,
            })
        else:
            events.append({
                'type': 'status_resisted',
                'effect': effect_type,
                'target': t.name,
            })

    return events
