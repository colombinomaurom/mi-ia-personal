"""
Módulo Damage - Calculadora de daño centralizada.
Usa formulas.py para cálculos y reporta eventos detallados.
"""
import random
from .formulas import calculate_damage, calculate_heal
from .effects import apply_status_effect


def execute_damage_skill(attacker, targets: list, skill: dict,
                         all_heroes: list, all_enemies: list) -> list:
    """
    Ejecuta una habilidad de daño contra uno o más objetivos.
    Retorna lista de eventos para el log de combate.
    """
    events = []
    hits = skill.get('hits', 1)

    for target in targets:
        if not target.is_alive:
            continue

        # Si el objetivo está dormido, el golpe lo despierta
        was_sleeping = any(e['type'] == 'sleep' for e in target.status_effects)
        if was_sleeping:
            target.status_effects = [e for e in target.status_effects
                                      if e['type'] != 'sleep']
            events.append({
                'type': 'sleep_broken',
                'target': target.name,
                'target_id': target.id,
                'message': f'{target.name} se despertó al recibir daño!'
            })

        total_damage = 0
        hit_crits = 0

        for hit_num in range(hits):
            dmg, is_crit, is_dodged, elem_mult = calculate_damage(
                attacker, target, skill
            )

            if is_dodged:
                events.append({
                    'type': 'dodge',
                    'attacker': attacker.name,
                    'target': target.name,
                    'target_id': target.id,
                    'skill': skill['name'],
                    'message': f'{target.name} esquivó el ataque!'
                })
                continue

            # Aplicar daño
            actual = target.take_damage(dmg)
            total_damage += actual
            attacker.total_damage_dealt += actual

            # El atacante gana Cosmo por dar daño (solo héroes)
            from entities import Hero
            if isinstance(attacker, Hero):
                attacker.gain_cosmo(max(2, int(actual / attacker.max_hp * 15)))

            if is_crit:
                hit_crits += 1

            # Generar evento de daño individual (para multi-golpe)
            if hits > 1:
                events.append({
                    'type': 'damage',
                    'attacker': attacker.name,
                    'attacker_id': attacker.id,
                    'target': target.name,
                    'target_id': target.id,
                    'skill': skill['name'],
                    'skill_icon': skill.get('icon', '⚔️'),
                    'damage': actual,
                    'is_crit': is_crit,
                    'hit_num': hit_num + 1,
                    'total_hits': hits,
                    'element_bonus': elem_mult > 1.0,
                    'target_hp': target.current_hp,
                    'target_max_hp': target.max_hp,
                })

            if not target.is_alive:
                break

        # Evento resumen (para habilidades multi-golpe o golpe único)
        event_data = {
            'type': 'damage_summary' if hits > 1 else 'damage',
            'attacker': attacker.name,
            'attacker_id': attacker.id,
            'target': target.name,
            'target_id': target.id,
            'skill': skill['name'],
            'skill_icon': skill.get('icon', '⚔️'),
            'damage': total_damage,
            'hits': hits,
            'crits': hit_crits,
            'is_crit': hit_crits > 0,
            'target_hp': target.current_hp,
            'target_max_hp': target.max_hp,
            'target_alive': target.is_alive,
        }

        if hits == 1:
            events.append(event_data)
        else:
            # Para multi-hit solo ponemos el resumen
            events.append({
                **event_data,
                'message': f'{attacker.name} usó {skill["name"]} ({hits} golpes, {total_damage} daño total)'
            })

        # Registrar muerte
        if not target.is_alive:
            events.append({
                'type': 'death',
                'target': target.name,
                'target_id': target.id,
                'killer': attacker.name,
            })
            attacker.kills += 1

        # Aplicar efectos de estado
        if target.is_alive or skill.get('status_effect') == 'death_mark':
            effect_events = apply_status_effect(target, skill, attacker, random)
            events.extend(effect_events)

        # Drenaje de MP (soul_drain)
        if skill.get('status_effect') == 'mp_drain' and target.is_alive:
            amount = skill.get('mp_drain_amount', 80)
            stolen = target.steal_mp(amount)
            attacker.restore_mp(stolen)
            if stolen > 0:
                events.append({
                    'type': 'mp_drain',
                    'attacker': attacker.name,
                    'target': target.name,
                    'amount': stolen,
                })

    return events


def execute_heal_skill(caster, targets: list, skill: dict) -> list:
    """Ejecuta una habilidad de curación."""
    events = []
    heal_amount = calculate_heal(caster, skill)

    for target in targets:
        if not target.is_alive:
            continue
        actual_heal = target.heal(heal_amount)
        events.append({
            'type': 'heal',
            'caster': caster.name,
            'caster_id': caster.id,
            'target': target.name,
            'target_id': target.id,
            'skill': skill['name'],
            'skill_icon': skill.get('icon', '💚'),
            'amount': actual_heal,
            'target_hp': target.current_hp,
            'target_max_hp': target.max_hp,
        })

    # Aplicar efectos de estado (buffs a aliados)
    status_target = skill.get('status_target', 'target')
    if status_target == 'all_allies':
        for target in targets:
            if target.is_alive:
                effect_events = apply_status_effect(target, skill, caster, random)
                events.extend(effect_events)
    elif skill.get('status_effect'):
        for target in targets:
            if target.is_alive:
                effect_events = apply_status_effect(target, skill, caster, random)
                events.extend(effect_events)

    return events


def execute_buff_skill(caster, targets: list, skill: dict) -> list:
    """Ejecuta una habilidad de buff/debuff puro (sin daño)."""
    events = []
    effect_type = skill.get('status_effect')

    for target in targets:
        if not target.is_alive:
            continue

        # Habilidades de escudo
        if effect_type == 'shield':
            shield_pct = skill.get('shield_pct', 0.25)
            shield_value = int(target.max_hp * shield_pct)
            effect = {
                'type': 'shield',
                'duration': skill.get('status_duration', 2),
                'value': shield_value,
                'source': caster.name,
                'name': 'Escudo',
                'icon': '🛡️',
                'color': '#4169E1',
                'dot_pct': 0,
            }
            target.add_status_effect(effect)
            events.append({
                'type': 'shield_applied',
                'caster': caster.name,
                'target': target.name,
                'target_id': target.id,
                'skill': skill['name'],
                'skill_icon': skill.get('icon', '🛡️'),
                'shield_value': shield_value,
            })
        else:
            # Aplicar efectos de estado normales
            effect_events = apply_status_effect(target, skill, caster, random)
            events.extend(effect_events)

    return events
