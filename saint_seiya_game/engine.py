"""
Módulo Engine - Motor central del juego.
Gestiona el estado del combate, el orden de turnos y la lógica de victoria/derrota.
"""
import random
from entities import Hero, Enemy
from data.database import init_db, load_all_heroes, load_all_enemies
from combat.skills import get_skill, get_skills_for
from combat.formulas import calculate_turn_order
from combat.synergy import calculate_synergies, apply_synergy_bonuses
from combat.executor import execute_action, process_turn_start
from combat.ai import ai_choose_action


class BattleState:
    """Enum-like para el estado del combate."""
    IDLE = 'idle'
    BATTLE_START = 'battle_start'
    PLAYER_TURN = 'player_turn'
    ENEMY_TURN = 'enemy_turn'
    BATTLE_END = 'battle_end'
    VICTORY = 'victory'
    DEFEAT = 'defeat'


class GameEngine:
    """Motor principal del juego. Mantiene el estado del combate."""

    def __init__(self, difficulty: str = 'normal'):
        self.difficulty = difficulty
        self.heroes: list[Hero] = []
        self.enemies: list[Enemy] = []
        self.turn_order: list = []
        self.current_turn_index: int = 0
        self.turn_number: int = 0
        self.state: str = BattleState.IDLE
        self.battle_log: list = []
        self.active_synergies: list = []
        self.total_turns: int = 0

        # Inicializar DB
        init_db()

    # ============================================================
    # INICIO DE COMBATE
    # ============================================================

    def start_battle(self) -> dict:
        """Inicializa un nuevo combate. Carga héroes y enemigos de la BD."""
        self.battle_log = []
        self.turn_number = 1
        self.current_turn_index = 0

        # Cargar datos de BD
        hero_data = load_all_heroes()
        enemy_data = load_all_enemies()

        # Crear instancias
        self.heroes = [Hero(h) for h in hero_data]
        self.enemies = [Enemy(e) for e in enemy_data]

        # Calcular y aplicar sinergias de héroes
        synergies, bonuses = calculate_synergies(self.heroes)
        self.active_synergies = synergies
        if bonuses:
            apply_synergy_bonuses(self.heroes, bonuses)

        # Calcular orden de turnos inicial
        all_fighters = self.heroes + self.enemies
        self.turn_order = calculate_turn_order(all_fighters)

        self.state = BattleState.PLAYER_TURN if self._current_fighter_is_hero() \
            else BattleState.ENEMY_TURN

        # Log de inicio
        log_entry = {
            'type': 'battle_start',
            'message': '⚔️ ¡El combate ha comenzado!',
            'turn': 1,
            'synergies': [s['name'] for s in synergies],
        }
        self.battle_log.append(log_entry)

        if synergies:
            for syn in synergies:
                self.battle_log.append({
                    'type': 'synergy',
                    'message': f'✨ Sinergia activada: {syn["name"]} — {syn["description"]}',
                })

        return self.get_state()

    # ============================================================
    # TURNO DEL JUGADOR
    # ============================================================

    def player_action(self, hero_id: int, skill_id: str, target_id: int) -> dict:
        """
        Procesa la acción del jugador para el héroe en turno.

        Args:
            hero_id: ID del héroe que actúa
            skill_id: ID de la habilidad a usar
            target_id: ID del objetivo (o -1 para AOE)

        Returns:
            Estado actualizado + eventos del turno
        """
        events = []

        if self.state != BattleState.PLAYER_TURN:
            return {'error': 'No es turno del jugador', 'state': self.get_state()}

        hero = self._get_fighter_by_id(hero_id, 'hero')
        if not hero:
            return {'error': f'Héroe {hero_id} no encontrado', 'state': self.get_state()}

        # Verificar que es el turno de ESTE héroe
        current = self._current_fighter()
        if not current or current.id != hero_id:
            return {'error': 'No es el turno de este héroe', 'state': self.get_state()}

        # Verificar si el héroe está aturdido
        if hero.is_stunned():
            stun_type = next((e['type'] for e in hero.status_effects
                              if e['type'] in ['stun', 'freeze', 'petrify', 'sleep', 'bind']),
                             'stun')
            events.append({
                'type': 'stunned',
                'fighter': hero.name,
                'effect': stun_type,
                'message': f'🚫 {hero.name} no puede actuar ({stun_type})!'
            })
            self._add_to_log(events)
            self._advance_turn()
            events.extend(self._process_enemy_turns())
            return {'events': events, 'state': self.get_state()}

        # Resolver objetivo
        target = None
        if target_id != -1:
            target = self._get_fighter_by_id(target_id)

        # Ejecutar acción
        action_events = execute_action(
            hero, skill_id, target, self.heroes, self.enemies
        )
        events.extend(action_events)

        # Verificar muertes y actualizar estado
        self._check_deaths(events)
        self._add_to_log(events)

        # Verificar fin de combate
        end_check = self._check_battle_end()
        if end_check:
            return {'events': events, 'state': self.get_state()}

        # Avanzar al siguiente turno
        self._advance_turn()

        # Procesar turnos de enemigos hasta que llegue el turno de un héroe
        enemy_events = self._process_enemy_turns()
        events.extend(enemy_events)

        return {'events': events, 'state': self.get_state()}

    # ============================================================
    # TURNOS DE ENEMIGOS (IA)
    # ============================================================

    def _process_enemy_turns(self) -> list:
        """Procesa todos los turnos de enemigos consecutivos hasta un turno de héroe."""
        all_events = []

        while True:
            current = self._current_fighter()
            if current is None:
                break

            if current.team == 'hero':
                self.state = BattleState.PLAYER_TURN
                break

            if not current.is_alive:
                self._advance_turn()
                continue

            # Proceso de inicio de turno del enemigo
            turn_start_events = process_turn_start(current)
            all_events.extend(turn_start_events)

            if not current.is_alive:
                self._check_deaths(turn_start_events)
                if self._check_battle_end():
                    return all_events
                self._advance_turn()
                continue

            # Turno del enemigo: IA decide acción
            alive_heroes = [h for h in self.heroes if h.is_alive]
            if not alive_heroes:
                break

            # Si está aturdido, saltar turno
            if current.is_stunned():
                stun_type = next((e['type'] for e in current.status_effects
                                  if e['type'] in ['stun', 'freeze', 'petrify', 'sleep', 'bind']),
                                 'stun')
                all_events.append({
                    'type': 'stunned',
                    'fighter': current.name,
                    'effect': stun_type,
                    'message': f'🚫 {current.name} no puede actuar ({stun_type})!'
                })
            else:
                # IA elige acción
                skill, target = ai_choose_action(current, alive_heroes, self.difficulty)

                if skill and target is not None:
                    action_events = execute_action(
                        current, skill['id'], target,
                        self.heroes, self.enemies
                    )
                    all_events.extend(action_events)
                    self._check_deaths(action_events)

            self._add_to_log(all_events[-20:])  # Solo log reciente

            # Verificar fin de combate
            if self._check_battle_end():
                return all_events

            self._advance_turn()

        return all_events

    # ============================================================
    # ACCIÓN ESPECIAL: ESCAPAR
    # ============================================================

    def flee_battle(self) -> dict:
        """El jugador huye del combate."""
        self.state = BattleState.DEFEAT
        self.battle_log.append({
            'type': 'flee',
            'message': '🏃 Los héroes huyen del combate...',
        })
        return {'events': [{'type': 'flee', 'message': '🏃 Huiste del combate!'}],
                'state': self.get_state()}

    # ============================================================
    # HELPERS INTERNOS
    # ============================================================

    def _current_fighter(self):
        """Retorna el combatiente en turno actual."""
        if not self.turn_order:
            return None

        # Buscar el siguiente combatiente vivo
        attempts = 0
        while attempts < len(self.turn_order) * 2:
            if self.current_turn_index >= len(self.turn_order):
                self._next_round()
            fighter = self.turn_order[self.current_turn_index]
            if fighter.is_alive:
                return fighter
            self.current_turn_index += 1
            attempts += 1
        return None

    def _current_fighter_is_hero(self) -> bool:
        fighter = self._current_fighter()
        return fighter is not None and fighter.team == 'hero'

    def _advance_turn(self):
        """Avanza al siguiente turno."""
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.turn_order):
            self._next_round()

    def _next_round(self):
        """Inicia un nuevo round: recalcula orden de turnos."""
        self.turn_number += 1
        self.current_turn_index = 0
        all_fighters = [f for f in (self.heroes + self.enemies) if f.is_alive]
        self.turn_order = calculate_turn_order(all_fighters)
        self.battle_log.append({
            'type': 'new_round',
            'message': f'🔄 — Ronda {self.turn_number} —',
            'turn': self.turn_number,
        })

        # Proceso de inicio del turno para cada combatiente (ahora en process_turn_start)

    def _get_fighter_by_id(self, fighter_id: int, team: str = None):
        """Busca un combatiente por ID."""
        all_fighters = self.heroes + self.enemies
        for f in all_fighters:
            if f.id == fighter_id:
                if team is None or f.team == team:
                    return f
        return None

    def _check_deaths(self, events: list):
        """Marca como muertos los combatientes con HP = 0."""
        for f in self.heroes + self.enemies:
            if f.current_hp <= 0 and f.is_alive:
                f.is_alive = False

    def _check_battle_end(self) -> bool:
        """Verifica si el combate terminó. Retorna True si terminó."""
        heroes_alive = [h for h in self.heroes if h.is_alive]
        enemies_alive = [e for e in self.enemies if e.is_alive]

        if not enemies_alive:
            self.state = BattleState.VICTORY
            self.battle_log.append({
                'type': 'victory',
                'message': '🏆 ¡VICTORIA! Los Santos de Bronce han triunfado!',
            })
            return True

        if not heroes_alive:
            self.state = BattleState.DEFEAT
            self.battle_log.append({
                'type': 'defeat',
                'message': '💀 DERROTA... Los Santos han caído en batalla.',
            })
            return True

        return False

    def _add_to_log(self, events: list):
        """Añade eventos al log de batalla formateados."""
        for event in events:
            if 'message' not in event:
                event['message'] = self._format_event(event)
            self.battle_log.append(event)
        # Limitar log a las últimas 200 entradas
        if len(self.battle_log) > 200:
            self.battle_log = self.battle_log[-200:]

    def _format_event(self, event: dict) -> str:
        """Formatea un evento como texto para el log."""
        etype = event.get('type', '')

        if etype == 'damage':
            crit_str = ' 💥CRÍTICO!' if event.get('is_crit') else ''
            return (f"{event.get('skill_icon','⚔️')} {event.get('attacker','?')} → "
                    f"{event.get('target','?')}: {event.get('damage', 0)} daño{crit_str}")

        elif etype == 'damage_summary':
            crits = event.get('crits', 0)
            crit_str = f' ({crits} CRÍTICO{"S" if crits > 1 else ""}!)' if crits else ''
            return (f"{event.get('skill_icon','⚔️')} {event.get('attacker','?')} usó "
                    f"{event.get('skill','?')} ({event.get('hits',1)} golpes) → "
                    f"{event.get('target','?')}: {event.get('damage', 0)} daño total{crit_str}")

        elif etype == 'skill_used':
            return (f"⚡ {event.get('caster','?')} usa "
                    f"{event.get('skill_icon','')} {event.get('skill','?')} "
                    f"[MP: -{event.get('mp_cost',0)}]")

        elif etype == 'heal':
            return (f"💚 {event.get('caster','?')} cura a "
                    f"{event.get('target','?')}: +{event.get('amount',0)} HP")

        elif etype == 'status_applied':
            return (f"{event.get('icon','❓')} {event.get('target','?')} recibe "
                    f"{event.get('name', event.get('effect','?'))} "
                    f"por {event.get('duration',1)} turno(s)")

        elif etype == 'death':
            return f"💀 {event.get('target','?')} ha sido derrotado!"

        elif etype == 'dot':
            return (f"{event.get('icon','🔥')} {event.get('target','?')} sufre "
                    f"{event.get('damage',0)} daño por {event.get('effect','efecto')}")

        elif etype == 'shield_applied':
            return (f"🛡️ {event.get('target','?')} recibe un escudo de "
                    f"{event.get('shield_value',0)} HP")

        elif etype == 'dodge':
            return f"💨 {event.get('target','?')} esquivó el ataque!"

        elif etype == 'confusion_trigger':
            return f"🌀 {event.get('message', '')}"

        return event.get('message', str(event))

    # ============================================================
    # SERIALIZACIÓN DEL ESTADO
    # ============================================================

    def get_state(self) -> dict:
        """Retorna el estado completo del combate como diccionario."""
        current = self._current_fighter()

        # Obtener info del turno actual
        current_fighter_data = None
        current_skills = []
        if current:
            current_fighter_data = {
                'id': current.id,
                'name': current.name,
                'team': current.team,
            }
            from combat.skills import get_skills_for
            current_skills = get_skills_for(current.skill_ids)

        # Turno order serializado (solo los vivos)
        turn_order_info = []
        for f in self.turn_order:
            if f.is_alive:
                turn_order_info.append({
                    'id': f.id,
                    'name': f.name,
                    'team': f.team,
                    'icon': f.icon,
                    'spd': int(f.effective_spd),
                })

        return {
            'heroes': [h.to_dict() for h in self.heroes],
            'enemies': [e.to_dict() for e in self.enemies],
            'state': self.state,
            'turn_number': self.turn_number,
            'current_fighter': current_fighter_data,
            'current_fighter_skills': current_skills,
            'turn_order': turn_order_info,
            'battle_log': self.battle_log[-30:],  # Últimos 30 eventos
            'active_synergies': self.active_synergies,
            'difficulty': self.difficulty,
        }
