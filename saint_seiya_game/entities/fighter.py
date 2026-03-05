"""
Módulo Fighter - Clase base para todos los combatientes (héroes y enemigos).
Define estadísticas, mecánicas de daño/curación y sistema de efectos de estado.
"""
import copy


class Fighter:
    """Clase base para todos los combatientes del juego."""

    def __init__(self, data: dict):
        self.id = data['id']
        self.name = data['name']
        self.title = data.get('title', '')
        self.icon = data.get('icon', '⚔️')
        self.element = data.get('element', 'neutral')
        self.team = data.get('team', 'enemy')
        self.level = data.get('level', 1)
        self.description = data.get('description', '')

        # Stats base
        self.max_hp = data['hp']
        self.current_hp = data['hp']
        self.max_mp = data['mp']
        self.current_mp = data['mp']
        self.base_atk = data['atk']
        self.base_def = data['def']
        self.base_spd = data['spd']
        self.crit_rate = data.get('crit_rate', 15)   # %
        self.crit_dmg = data.get('crit_dmg', 150)    # % del daño base
        self.dodge = data.get('dodge', 5)             # %

        # Habilidades
        self.skill_ids = data.get('skills', [])
        self.passive = data.get('passive', None)

        # Estado en combate
        self.is_alive = True
        self.status_effects = []    # Lista de efectos activos
        self.buffs = {}             # Buffs activos {nombre: {stat: valor, duration}}
        self.debuffs = {}           # Debuffs activos
        self.cooldowns = {}         # {skill_id: turnos_restantes}
        self.turn_count = 0
        self.revive_used = False    # Para pasiva de Ikki

        # Sinergias
        self.synergy_tags = data.get('synergy_tags', [])

        # Métricas de combate
        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.total_heals = 0
        self.kills = 0

    # --- PROPIEDADES CALCULADAS ---

    @property
    def effective_atk(self):
        """ATK efectivo considerando buffs/debuffs."""
        mod = 1.0
        for effect in self.status_effects:
            if effect['type'] == 'atk_up':
                mod += effect['value']
            elif effect['type'] == 'atk_down':
                mod -= effect['value']
        for buff in self.buffs.values():
            if 'atk' in buff:
                mod += buff['atk']
        return max(0.1, mod) * self.base_atk

    @property
    def effective_def(self):
        """DEF efectivo considerando buffs/debuffs."""
        mod = 1.0
        for effect in self.status_effects:
            if effect['type'] == 'def_up':
                mod += effect['value']
            elif effect['type'] == 'def_down':
                mod -= effect['value']
        for buff in self.buffs.values():
            if 'def' in buff:
                mod += buff['def']
        return max(0.1, mod) * self.base_def

    @property
    def effective_spd(self):
        """SPD efectivo considerando buffs/debuffs."""
        mod = 1.0
        for effect in self.status_effects:
            if effect['type'] == 'spd_up':
                mod += effect['value']
            elif effect['type'] == 'spd_down':
                mod -= effect['value']
        return max(0.1, mod) * self.base_spd

    @property
    def effective_crit_rate(self):
        """Tasa de crítico efectiva."""
        bonus = 0
        for effect in self.status_effects:
            if effect['type'] == 'crit_up':
                bonus += effect['value']
        return min(95, self.crit_rate + bonus)

    @property
    def effective_dodge(self):
        """Esquiva efectiva."""
        bonus = 0
        for effect in self.status_effects:
            if effect['type'] == 'dodge_up':
                bonus += effect['value']
        return min(60, self.dodge + bonus)

    @property
    def hp_percent(self):
        return (self.current_hp / self.max_hp) * 100

    @property
    def mp_percent(self):
        return (self.current_mp / self.max_mp) * 100

    # --- ESTADO DE CONTROL ---

    def is_stunned(self):
        return any(e['type'] in ['stun', 'freeze', 'petrify', 'sleep', 'bind']
                   for e in self.status_effects)

    def is_confused(self):
        return any(e['type'] == 'confusion' for e in self.status_effects)

    def is_silenced(self):
        return any(e['type'] == 'silence' for e in self.status_effects)

    def has_shield(self):
        return any(e['type'] == 'shield' for e in self.status_effects)

    def get_shield_value(self):
        total = 0
        for e in self.status_effects:
            if e['type'] == 'shield':
                total += e.get('value', 0)
        return total

    def has_death_mark(self):
        return any(e['type'] == 'death_mark' for e in self.status_effects)

    # --- ACCIONES ---

    def take_damage(self, damage: int, ignore_shield=False):
        """Aplica daño al combatiente. Retorna daño real recibido."""
        actual = max(1, int(damage))

        # Verificar escudo
        if not ignore_shield and self.has_shield():
            shield_val = self.get_shield_value()
            if shield_val >= actual:
                self._reduce_shield(actual)
                return 0
            else:
                actual -= shield_val
                self._clear_shields()

        # Verificar marca de muerte (siguiente golpe x2)
        if self.has_death_mark():
            actual = actual * 2
            self.status_effects = [e for e in self.status_effects
                                   if e['type'] != 'death_mark']

        self.current_hp = max(0, self.current_hp - actual)
        self.total_damage_taken += actual

        if self.current_hp <= 0:
            self.current_hp = 0
            # Pasiva de Ikki: Resurrección
            if self.passive == 'undying_will' and not self.revive_used:
                self.revive_used = True
                self.current_hp = int(self.max_hp * 0.30)
                return actual  # Devuelve el daño pero el personaje revive
            self.is_alive = False

        return actual

    def _reduce_shield(self, amount):
        for e in self.status_effects:
            if e['type'] == 'shield':
                e['value'] = max(0, e['value'] - amount)
                if e['value'] == 0:
                    self.status_effects.remove(e)
                return

    def _clear_shields(self):
        self.status_effects = [e for e in self.status_effects
                               if e['type'] != 'shield']

    def heal(self, amount: int):
        """Cura HP. Retorna cantidad real curada."""
        amount = int(amount)
        prev = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        actual = self.current_hp - prev
        self.total_heals += actual
        return actual

    def use_mp(self, cost: int) -> bool:
        """Intenta gastar MP. Retorna True si tuvo éxito."""
        if self.current_mp >= cost:
            self.current_mp -= cost
            return True
        return False

    def restore_mp(self, amount: int):
        self.current_mp = min(self.max_mp, self.current_mp + amount)

    def steal_mp(self, amount: int) -> int:
        """Roba MP de este combatiente. Retorna cantidad robada."""
        stolen = min(self.current_mp, amount)
        self.current_mp -= stolen
        return stolen

    # --- EFECTOS DE ESTADO ---

    def add_status_effect(self, effect: dict):
        """Agrega un efecto de estado. Si ya existe, renueva duración."""
        existing = next((e for e in self.status_effects
                        if e['type'] == effect['type']), None)
        if existing:
            existing['duration'] = max(existing['duration'], effect['duration'])
        else:
            self.status_effects.append(copy.deepcopy(effect))

    def add_buff(self, name: str, buff_data: dict):
        self.buffs[name] = copy.deepcopy(buff_data)

    def add_debuff(self, name: str, debuff_data: dict):
        self.debuffs[name] = copy.deepcopy(debuff_data)

    def tick_status_effects(self):
        """Procesa efectos al inicio de turno. Retorna lista de eventos."""
        events = []

        for effect in self.status_effects[:]:
            etype = effect['type']

            if etype == 'burn':
                dmg = int(self.max_hp * effect.get('dot_pct', 0.04))
                self.current_hp = max(0, self.current_hp - dmg)
                if self.current_hp == 0:
                    self.is_alive = False
                events.append({
                    'type': 'dot',
                    'effect': 'burn',
                    'target': self.name,
                    'damage': dmg,
                    'icon': '🔥'
                })
            elif etype == 'bleed':
                dmg = int(self.max_hp * effect.get('dot_pct', 0.035))
                self.current_hp = max(0, self.current_hp - dmg)
                if self.current_hp == 0:
                    self.is_alive = False
                events.append({
                    'type': 'dot',
                    'effect': 'bleed',
                    'target': self.name,
                    'damage': dmg,
                    'icon': '🩸'
                })

            effect['duration'] -= 1

        # Limpiar efectos expirados
        expired = [e for e in self.status_effects if e['duration'] <= 0]
        for e in expired:
            events.append({
                'type': 'effect_expired',
                'effect': e['type'],
                'target': self.name
            })
        self.status_effects = [e for e in self.status_effects if e['duration'] > 0]

        # Tick de buffs/debuffs
        for name, buff in list(self.buffs.items()):
            buff['duration'] = buff.get('duration', 0) - 1
            if buff['duration'] <= 0:
                del self.buffs[name]

        return events

    def get_cooldown(self, skill_id: str) -> int:
        return self.cooldowns.get(skill_id, 0)

    def set_cooldown(self, skill_id: str, turns: int):
        self.cooldowns[skill_id] = turns

    def tick_cooldowns(self):
        for skill_id in list(self.cooldowns.keys()):
            self.cooldowns[skill_id] = max(0, self.cooldowns[skill_id] - 1)
            if self.cooldowns[skill_id] == 0:
                del self.cooldowns[skill_id]

    # --- SERIALIZACIÓN ---

    def to_dict(self) -> dict:
        """Convierte el combatiente a diccionario para JSON."""
        return {
            'id': self.id,
            'name': self.name,
            'title': self.title,
            'icon': self.icon,
            'element': self.element,
            'team': self.team,
            'level': self.level,
            'max_hp': self.max_hp,
            'current_hp': self.current_hp,
            'hp_percent': round(self.hp_percent, 1),
            'max_mp': self.max_mp,
            'current_mp': self.current_mp,
            'mp_percent': round(self.mp_percent, 1),
            'atk': int(self.effective_atk),
            'def': int(self.effective_def),
            'spd': int(self.effective_spd),
            'crit_rate': self.effective_crit_rate,
            'crit_dmg': self.crit_dmg,
            'dodge': self.effective_dodge,
            'skill_ids': self.skill_ids,
            'passive': self.passive,
            'status_effects': self.status_effects,
            'buffs': self.buffs,
            'debuffs': self.debuffs,
            'cooldowns': self.cooldowns,
            'is_alive': self.is_alive,
            'synergy_tags': self.synergy_tags,
            'description': self.description,
            'total_damage_dealt': self.total_damage_dealt,
            'total_damage_taken': self.total_damage_taken,
        }
