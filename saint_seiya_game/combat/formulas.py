"""
Módulo Formulas - Todas las fórmulas matemáticas del sistema de combate.
Daño, críticos, esquiva, sinergia elemental y modificadores de estado.
"""
import random

# Tabla de ventajas elementales
# 1.3 = ventaja, 0.7 = desventaja, 1.0 = neutral
ELEMENT_CHART = {
    #          light  dark   fire   ice    earth  wind   neutral
    "light":  [1.0,   1.3,   1.0,   1.0,   1.0,   1.0,   1.0],
    "dark":   [0.7,   1.0,   1.0,   1.0,   1.0,   1.0,   1.0],
    "fire":   [1.0,   1.0,   1.0,   0.7,   1.3,   1.3,   1.0],
    "ice":    [1.0,   1.0,   1.3,   1.0,   1.0,   0.7,   1.0],
    "earth":  [1.0,   1.0,   0.7,   1.0,   1.0,   1.3,   1.0],
    "wind":   [1.0,   1.0,   0.7,   1.3,   0.7,   1.0,   1.0],
    "neutral":[1.0,   1.0,   1.0,   1.0,   1.0,   1.0,   1.0],
}
ELEMENT_ORDER = ["light", "dark", "fire", "ice", "earth", "wind", "neutral"]


def get_element_multiplier(atk_element: str, def_element: str) -> float:
    """Retorna el multiplicador elemental entre atacante y defensor."""
    row = ELEMENT_CHART.get(atk_element, ELEMENT_CHART["neutral"])
    idx = ELEMENT_ORDER.index(def_element) if def_element in ELEMENT_ORDER else 6
    return row[idx]


def calculate_defense_reduction(effective_def: float, armor_pen: float = 0.0) -> float:
    """
    Fórmula de reducción de defensa con disminución de retornos.
    La defensa nunca puede reducir 100% del daño.
    Armor pen (0-1) ignora ese porcentaje de la defensa.
    """
    penetrated_def = effective_def * (1.0 - armor_pen)
    # Fórmula: reduccion = DEF / (DEF + 600)  -> máximo ~94%
    reduction = penetrated_def / (penetrated_def + 600.0)
    return min(0.80, reduction)  # Cap en 80% de reducción


def check_critical(crit_rate: float) -> bool:
    """Comprueba si el ataque es un golpe crítico."""
    return random.randint(1, 100) <= crit_rate


def check_dodge(dodge_rate: float, bypass_dodge: bool = False) -> bool:
    """Comprueba si el defensor esquiva el ataque."""
    if bypass_dodge:
        return False
    return random.randint(1, 100) <= dodge_rate


def apply_variance(damage: float, variance: float = 0.10) -> int:
    """Aplica varianza aleatoria al daño (±variance%)."""
    min_v = 1.0 - variance
    max_v = 1.0 + variance
    return max(1, int(damage * random.uniform(min_v, max_v)))


def calculate_base_damage(attacker_atk: float, skill_power: float) -> float:
    """Calcula el daño base sin contar defensa."""
    return attacker_atk * skill_power


def calculate_damage(attacker, defender, skill: dict) -> tuple:
    """
    Calcula el daño final de un ataque.

    Args:
        attacker: Instancia de Fighter (atacante)
        defender: Instancia de Fighter (defensor)
        skill: Diccionario de la habilidad

    Returns:
        Tuple (damage: int, is_crit: bool, is_dodged: bool, element_bonus: float)
    """
    power = skill.get('power', 1.0)
    armor_pen = skill.get('armor_pen', 0.0)
    bypass_dodge = skill.get('bypass_dodge', False)

    # 1. Comprobar esquiva
    dodge_rate = defender.effective_dodge
    if check_dodge(dodge_rate, bypass_dodge):
        return 0, False, True, 1.0

    # 2. Daño base
    base_dmg = calculate_base_damage(attacker.effective_atk, power)

    # 3. Reducción de defensa
    def_reduction = calculate_defense_reduction(defender.effective_def, armor_pen)
    damage = base_dmg * (1.0 - def_reduction)

    # 4. Multiplicador elemental
    skill_element = skill.get('element', attacker.element)
    element_mult = get_element_multiplier(skill_element, defender.element)
    damage *= element_mult

    # 5. Bonus vs enemigo congelado (aurora_execution)
    if skill.get('bonus_vs_frozen'):
        is_frozen = any(e['type'] == 'freeze' for e in defender.status_effects)
        if is_frozen:
            damage *= skill['bonus_vs_frozen']

    # 6. Bono de Cosmo de héroe (si aplica)
    from entities import Hero
    if isinstance(attacker, Hero):
        damage *= attacker.cosmo_burst_bonus()

    # 7. Crítico
    is_crit = check_critical(attacker.effective_crit_rate)
    if is_crit:
        crit_multiplier = attacker.crit_dmg / 100.0
        damage *= crit_multiplier

    # 8. Varianza aleatoria
    final_damage = apply_variance(damage)

    return final_damage, is_crit, False, element_mult


def calculate_heal(caster, skill: dict) -> int:
    """Calcula la cantidad de curación de una habilidad."""
    heal_pct = skill.get('heal_pct', 0.3)
    # La curación se basa en el HP máximo del lanzador
    return int(caster.max_hp * heal_pct)


def calculate_turn_order(fighters: list) -> list:
    """
    Calcula el orden de turnos basándose en SPD.
    Desempate por randomness, luego por id.
    """
    alive = [f for f in fighters if f.is_alive]
    # Ordenar por SPD efectiva descendente, con pequeño ruido para desempate
    ordered = sorted(
        alive,
        key=lambda f: (f.effective_spd + random.uniform(0, 5), f.id),
        reverse=True
    )
    return ordered
