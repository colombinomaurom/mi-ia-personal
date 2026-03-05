"""
Módulo AI - Inteligencia artificial de los enemigos.
Modular por dificultad: easy / normal / hard.
Cada estilo de IA determina la estrategia de selección de habilidades y objetivos.
"""
import random
from .skills import get_skill


# ============================================================
# SELECTOR DE OBJETIVO
# ============================================================

def select_target_lowest_hp(targets: list):
    """Elige el objetivo con menor HP actual."""
    alive = [t for t in targets if t.is_alive]
    if not alive:
        return None
    return min(alive, key=lambda t: t.current_hp)


def select_target_highest_hp(targets: list):
    """Elige el objetivo con mayor HP actual."""
    alive = [t for t in targets if t.is_alive]
    if not alive:
        return None
    return max(alive, key=lambda t: t.current_hp)


def select_target_highest_atk(targets: list):
    """Elige el objetivo con mayor ATK (amenaza mayor)."""
    alive = [t for t in targets if t.is_alive]
    if not alive:
        return None
    return max(alive, key=lambda t: t.effective_atk)


def select_target_random(targets: list):
    """Elige un objetivo aleatorio."""
    alive = [t for t in targets if t.is_alive]
    if not alive:
        return None
    return random.choice(alive)


def select_target_no_status(targets: list, effect_type: str):
    """Elige un objetivo que no tenga un efecto específico."""
    alive = [t for t in targets if t.is_alive]
    no_effect = [t for t in alive
                 if not any(e['type'] == effect_type for e in t.status_effects)]
    if no_effect:
        return random.choice(no_effect)
    return random.choice(alive) if alive else None


# ============================================================
# SELECTOR DE HABILIDAD POR ESTILO
# ============================================================

def get_available_skills(enemy, difficulty: str = 'normal') -> list:
    """Retorna habilidades disponibles (con MP y sin cooldown)."""
    available = []
    for skill_id in enemy.skill_ids:
        skill = get_skill(skill_id)
        if not skill:
            continue

        # Verificar cooldown
        if enemy.get_cooldown(skill_id) > 0:
            continue

        # Verificar MP
        if enemy.current_mp < skill['mp_cost']:
            continue

        # Verificar requisito especial (blood_frenzy)
        if skill.get('requires_hp_below'):
            if enemy.hp_percent >= skill['requires_hp_below']:
                continue

        available.append(skill)

    return available


def ai_choose_action_aggressive(enemy, heroes: list, difficulty: str) -> tuple:
    """
    Estilo AGRESIVO: Siempre ataca, prefiere el héroe más débil.
    """
    available = get_available_skills(enemy, difficulty)
    alive_heroes = [h for h in heroes if h.is_alive]

    if not alive_heroes:
        return None, None

    # Preferir habilidades AOE si hay múltiples héroes
    aoe_skills = [s for s in available if s['target_type'] in ('all_enemies', 'all_enemies_random')]
    single_skills = [s for s in available if s['target_type'] == 'single_enemy']

    # En dificultad hard, usar AOE si hay 3+ héroes vivos
    if difficulty == 'hard' and len(alive_heroes) >= 3 and aoe_skills:
        skill = random.choice(aoe_skills)
    elif single_skills:
        # Elegir la habilidad más poderosa disponible
        if difficulty == 'hard':
            skill = max(single_skills, key=lambda s: s.get('power', 0))
        else:
            skill = random.choice(single_skills)
    elif available:
        skill = random.choice(available)
    else:
        skill = get_skill(enemy.skill_ids[0])  # Ataque básico siempre disponible

    # Seleccionar objetivo
    if skill['target_type'] == 'single_enemy':
        if difficulty == 'hard':
            target = select_target_lowest_hp(alive_heroes)
        else:
            target = select_target_random(alive_heroes)
    else:
        target = alive_heroes  # AOE

    return skill, target


def ai_choose_action_debuffer(enemy, heroes: list, difficulty: str) -> tuple:
    """
    Estilo DEBUFFER: Prioriza aplicar debuffs/control antes de atacar.
    """
    available = get_available_skills(enemy, difficulty)
    alive_heroes = [h for h in heroes if h.is_alive]

    if not alive_heroes:
        return None, None

    # Intentar aplicar debuffs primero
    debuff_skills = [s for s in available
                     if s['effect_type'] in ('debuff', 'mixed') and s['mp_cost'] > 0]

    # Buscar objetivos sin el debuff que queremos aplicar
    if debuff_skills and difficulty != 'easy':
        # Priorizar debuffs sobre héroes que no los tienen
        skill = debuff_skills[0] if difficulty == 'hard' else random.choice(debuff_skills)
        effect_type = skill.get('status_effect', '')
        target = select_target_no_status(alive_heroes, effect_type)
        if target:
            return skill, target

    # Si no hay debuffs disponibles, atacar
    attack_skills = [s for s in available
                     if s['effect_type'] in ('damage', 'mixed')]
    if attack_skills:
        skill = random.choice(attack_skills)
    elif available:
        skill = random.choice(available)
    else:
        skill = get_skill(enemy.skill_ids[0])

    if skill['target_type'] == 'single_enemy':
        target = select_target_lowest_hp(alive_heroes)
    else:
        target = alive_heroes

    return skill, target


def ai_choose_action_mixed(enemy, heroes: list, difficulty: str) -> tuple:
    """
    Estilo MIXTO: Balanceo entre ataques y efectos de estado.
    """
    available = get_available_skills(enemy, difficulty)
    alive_heroes = [h for h in heroes if h.is_alive]

    if not alive_heroes:
        return None, None

    if not available:
        skill = get_skill(enemy.skill_ids[0])
        return skill, select_target_random(alive_heroes)

    skill = random.choice(available)

    if skill['target_type'] == 'single_enemy':
        target = select_target_random(alive_heroes)
    else:
        target = alive_heroes

    return skill, target


def ai_choose_action_assassin(enemy, heroes: list, difficulty: str) -> tuple:
    """
    Estilo ASESINO: Prioriza matar al héroe más débil rápidamente.
    Aplica muerte_mark antes de atacar.
    """
    available = get_available_skills(enemy, difficulty)
    alive_heroes = [h for h in heroes if h.is_alive]

    if not alive_heroes:
        return None, None

    # Prioridad 1: Si hay un héroe marcado con death_mark, usar ataque fuerte
    marked_heroes = [h for h in alive_heroes
                     if any(e['type'] == 'death_mark' for e in h.status_effects)]
    if marked_heroes and difficulty != 'easy':
        attack_skills = [s for s in available
                         if s['effect_type'] == 'damage' and s['mp_cost'] > 0]
        if attack_skills:
            skill = max(attack_skills, key=lambda s: s.get('power', 0))
            return skill, marked_heroes[0]

    # Prioridad 2: Aplicar death_mark si está disponible
    mark_skill = next((s for s in available if s['id'] == 'death_mark'), None)
    if mark_skill and difficulty in ('normal', 'hard'):
        target = select_target_lowest_hp(alive_heroes)
        return mark_skill, target

    # Prioridad 3: Usar shadow_strike (con buff de crit)
    if not available:
        skill = get_skill(enemy.skill_ids[0])
    else:
        skill = random.choice(available)

    if skill['target_type'] == 'single_enemy':
        target = select_target_lowest_hp(alive_heroes)
    else:
        target = alive_heroes

    return skill, target


def ai_choose_action_berserker(enemy, heroes: list, difficulty: str) -> tuple:
    """
    Estilo BERSERKER: Usa blood_frenzy cuando puede, luego ataques pesados.
    """
    available = get_available_skills(enemy, difficulty)
    alive_heroes = [h for h in heroes if h.is_alive]

    if not alive_heroes:
        return None, None

    # Activar blood_frenzy si HP < 50%
    frenzy = next((s for s in available if s['id'] == 'blood_frenzy'), None)
    if frenzy and enemy.hp_percent < 50:
        return frenzy, enemy

    # AOE si hay 3+ objetivos
    aoe_skills = [s for s in available if s['target_type'] in ('all_enemies',)]
    if len(alive_heroes) >= 3 and aoe_skills:
        skill = aoe_skills[0]
        return skill, alive_heroes

    # Ataque más fuerte
    attack_skills = [s for s in available if s['effect_type'] == 'damage']
    if attack_skills:
        skill = max(attack_skills, key=lambda s: s.get('power', 0))
    elif available:
        skill = random.choice(available)
    else:
        skill = get_skill(enemy.skill_ids[0])

    if skill['target_type'] == 'single_enemy':
        target = select_target_highest_hp(alive_heroes) if difficulty == 'hard' \
            else select_target_random(alive_heroes)
    else:
        target = alive_heroes

    return skill, target


# ============================================================
# INTERFAZ PRINCIPAL DE IA
# ============================================================

AI_STYLE_MAP = {
    'aggressive': ai_choose_action_aggressive,
    'debuffer': ai_choose_action_debuffer,
    'mixed': ai_choose_action_mixed,
    'assassin': ai_choose_action_assassin,
    'berserker': ai_choose_action_berserker,
}


def ai_choose_action(enemy, heroes: list, difficulty: str = 'normal') -> tuple:
    """
    Punto de entrada principal de la IA.

    Args:
        enemy: Instancia de Enemy
        heroes: Lista de Heroes vivos
        difficulty: 'easy', 'normal', 'hard'

    Returns:
        (skill: dict, target: Fighter o list)
    """
    ai_style = getattr(enemy, 'ai_style', 'mixed')
    ai_func = AI_STYLE_MAP.get(ai_style, ai_choose_action_mixed)

    skill, target = ai_func(enemy, heroes, difficulty)

    # Fallback: si no hay habilidad disponible, usar ataque básico
    if skill is None:
        skill = get_skill(enemy.skill_ids[0])
        alive = [h for h in heroes if h.is_alive]
        target = random.choice(alive) if alive else None

    return skill, target
