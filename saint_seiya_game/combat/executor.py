"""
Módulo Executor - Ejecuta acciones de combate y genera el log de eventos.
Coordina damage.py, effects.py y skills.py para resolver cada acción.
"""
import random
from .skills import get_skill
from .damage import execute_damage_skill, execute_heal_skill, execute_buff_skill
from .effects import apply_status_effect


def resolve_targets(caster, skill: dict, target_input,
                    all_heroes: list, all_enemies: list) -> list:
    """
    Resuelve la lista de objetivos según el tipo de objetivo de la habilidad.

    Args:
        caster: Combatiente que ejecuta la acción
        skill: Datos de la habilidad
        target_input: Objetivo(s) elegido(s) (puede ser un Fighter o lista)
        all_heroes: Todos los héroes
        all_enemies: Todos los enemigos

    Returns:
        Lista de objetivos resueltos
    """
    target_type = skill.get('target_type', 'single_enemy')
    caster_team = caster.team

    # Determinar equipo aliado y enemigo
    if caster_team == 'hero':
        allies = [f for f in all_heroes if f.is_alive]
        enemies = [f for f in all_enemies if f.is_alive]
    else:
        allies = [f for f in all_enemies if f.is_alive]
        enemies = [f for f in all_heroes if f.is_alive]

    if target_type == 'single_enemy':
        if isinstance(target_input, list):
            return [target_input[0]] if target_input else []
        return [target_input] if target_input else []

    elif target_type == 'all_enemies':
        return enemies

    elif target_type == 'all_enemies_random':
        # N golpes distribuidos aleatoriamente
        hits = skill.get('hits', 5)
        if not enemies:
            return []
        return [random.choice(enemies) for _ in range(hits)]

    elif target_type == 'single_ally':
        if isinstance(target_input, list):
            return [target_input[0]] if target_input else []
        return [target_input] if target_input else []

    elif target_type == 'all_allies':
        return allies

    elif target_type == 'ally_lowest_hp':
        if not allies:
            return [caster]
        return [min(allies, key=lambda f: f.current_hp)]

    elif target_type == 'self':
        return [caster]

    return [target_input] if target_input else []


def execute_action(caster, skill_id: str, target_input,
                   all_heroes: list, all_enemies: list) -> list:
    """
    Ejecuta una acción de combate completa.

    Args:
        caster: Fighter que realiza la acción
        skill_id: ID de la habilidad a usar
        target_input: Objetivo(s) seleccionados
        all_heroes: Todos los héroes del combate
        all_enemies: Todos los enemigos del combate

    Returns:
        Lista de eventos generados por la acción
    """
    events = []

    skill = get_skill(skill_id)
    if not skill:
        return [{'type': 'error', 'message': f'Habilidad {skill_id} no encontrada'}]

    # Verificar silencio (no puede usar habilidades MP)
    if caster.is_silenced() and skill.get('mp_cost', 0) > 0:
        events.append({
            'type': 'silenced',
            'caster': caster.name,
            'message': f'{caster.name} está silenciado y no puede usar habilidades!'
        })
        return events

    # Verificar cooldown
    if caster.get_cooldown(skill_id) > 0:
        events.append({
            'type': 'cooldown',
            'caster': caster.name,
            'skill': skill['name'],
            'message': f'{skill["name"]} aún está en espera ({caster.get_cooldown(skill_id)} turnos)'
        })
        return events

    # Gastar MP
    mp_cost = skill.get('mp_cost', 0)
    if mp_cost > 0:
        if not caster.use_mp(mp_cost):
            events.append({
                'type': 'no_mp',
                'caster': caster.name,
                'skill': skill['name'],
                'message': f'{caster.name} no tiene MP suficiente para {skill["name"]}!'
            })
            return events

    # Registrar uso de habilidad
    events.append({
        'type': 'skill_used',
        'caster': caster.name,
        'caster_id': caster.id,
        'skill': skill['name'],
        'skill_id': skill_id,
        'skill_icon': skill.get('icon', '⚔️'),
        'mp_cost': mp_cost,
        'caster_mp': caster.current_mp,
    })

    # Si el caster está confundido: el objetivo se convierte en aliado random
    if caster.is_confused():
        if caster.team == 'hero':
            confused_targets = [h for h in all_heroes
                                if h.is_alive and h.id != caster.id]
        else:
            confused_targets = [e for e in all_enemies
                                if e.is_alive and e.id != caster.id]

        if confused_targets:
            target_input = random.choice(confused_targets)
            events.append({
                'type': 'confusion_trigger',
                'caster': caster.name,
                'new_target': target_input.name,
                'message': f'{caster.name} está confundido y ataca a {target_input.name}!'
            })

    # Resolver objetivos
    targets = resolve_targets(caster, skill, target_input, all_heroes, all_enemies)

    # Ejecutar según tipo de efecto
    effect_type = skill.get('effect_type', 'damage')

    if effect_type == 'damage':
        # Para all_enemies_random, resolve_targets ya generó la lista con repetición
        if skill['target_type'] == 'all_enemies_random':
            # Agrupar por objetivo para calcular daño por separado
            for target in targets:
                dmg_events = execute_damage_skill(
                    caster, [target],
                    {**skill, 'hits': 1},  # Cada entrada ya es un golpe
                    all_heroes, all_enemies
                )
                events.extend(dmg_events)
        else:
            dmg_events = execute_damage_skill(
                caster, targets, skill, all_heroes, all_enemies
            )
            events.extend(dmg_events)

    elif effect_type == 'heal':
        heal_events = execute_heal_skill(caster, targets, skill)
        events.extend(heal_events)

        # Si el skill también tiene buff para todos los aliados
        if skill.get('status_target') == 'all_allies':
            if caster.team == 'hero':
                buff_targets = [h for h in all_heroes if h.is_alive]
            else:
                buff_targets = [e for e in all_enemies if e.is_alive]
            for bt in buff_targets:
                apply_status_effect(bt, skill, caster, random)

    elif effect_type == 'buff':
        # Verificar si es para aliados o self
        if skill['target_type'] in ('all_allies', 'ally_lowest_hp', 'self'):
            buff_events = execute_buff_skill(caster, targets, skill)
            events.extend(buff_events)

    elif effect_type == 'debuff':
        # Debuff sin daño (phoenix_illusion, cursed_gaze)
        if skill.get('power', 0) > 0:
            dmg_events = execute_damage_skill(
                caster, targets, skill, all_heroes, all_enemies
            )
            events.extend(dmg_events)
        else:
            # Solo aplicar el efecto
            for target in targets:
                if target.is_alive:
                    effect_events = apply_status_effect(
                        target, skill, caster, random
                    )
                    events.extend(effect_events)

    elif effect_type == 'mixed':
        # Daño + efecto
        dmg_events = execute_damage_skill(
            caster, targets, skill, all_heroes, all_enemies
        )
        events.extend(dmg_events)

        # Buff especial sobre el caster (comet_punch)
        if skill.get('status_target') == 'self' and skill.get('status_effect'):
            apply_status_effect(caster, skill, caster, random)

    # Aplicar cooldown
    cooldown = skill.get('cooldown', 0)
    if cooldown > 0:
        caster.set_cooldown(skill_id, cooldown)

    # Regeneración de MP al final del turno (5 MP base)
    caster.restore_mp(5)

    return events


def process_turn_start(fighter) -> list:
    """
    Procesa el inicio del turno de un combatiente.
    Tick de efectos de estado, cooldowns, etc.
    Retorna lista de eventos.
    """
    events = []

    if not fighter.is_alive:
        return events

    # Tick de efectos (DOT, duración)
    status_events = fighter.tick_status_effects()
    events.extend(status_events)

    # Tick de cooldowns
    fighter.tick_cooldowns()

    # Verificar si murió por DOT
    if not fighter.is_alive:
        events.append({
            'type': 'death',
            'target': fighter.name,
            'target_id': fighter.id,
            'killer': 'Efecto de estado',
        })

    return events
