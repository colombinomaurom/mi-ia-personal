"""
Módulo Server - Servidor Flask que expone la API del juego y sirve la interfaz HTML.
"""
import os
import sys
from flask import Flask, jsonify, request, render_template, send_from_directory

# Agregar el directorio del juego al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import GameEngine, BattleState
from combat.skills import get_skills_for, ALL_SKILLS

# Crear app Flask
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'ui', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'ui', 'static'),
)

# Instancia global del motor de juego
engine = GameEngine(difficulty='normal')


# ============================================================
# RUTAS DE INTERFAZ
# ============================================================

@app.route('/')
def index():
    return render_template('hub.html')


@app.route('/combat')
def combat():
    return render_template('combat.html')


@app.route('/heroes')
def heroes_screen():
    return render_template('heroes.html')


# ============================================================
# API DEL JUEGO
# ============================================================

@app.route('/api/start_battle', methods=['POST'])
def start_battle():
    """Inicia un nuevo combate."""
    data = request.get_json() or {}
    difficulty = data.get('difficulty', 'normal')

    global engine
    engine = GameEngine(difficulty=difficulty)
    state = engine.start_battle()

    # Procesar turnos de enemigos si el primero en turno es enemigo
    if state['state'] == BattleState.ENEMY_TURN:
        enemy_events = engine._process_enemy_turns()
        state = engine.get_state()
        state['initial_enemy_events'] = enemy_events

    return jsonify({'success': True, 'state': state})


@app.route('/api/state', methods=['GET'])
def get_state():
    """Retorna el estado actual del combate."""
    return jsonify(engine.get_state())


@app.route('/api/action', methods=['POST'])
def player_action():
    """Ejecuta la acción del jugador."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Sin datos'}), 400

    hero_id = data.get('hero_id')
    skill_id = data.get('skill_id')
    target_id = data.get('target_id', -1)

    if not hero_id or not skill_id:
        return jsonify({'error': 'Faltan parámetros hero_id o skill_id'}), 400

    result = engine.player_action(int(hero_id), skill_id, int(target_id))
    return jsonify(result)


@app.route('/api/flee', methods=['POST'])
def flee():
    """El jugador huye del combate."""
    result = engine.flee_battle()
    return jsonify(result)


@app.route('/api/heroes', methods=['GET'])
def get_heroes():
    """Retorna todos los héroes del combate actual."""
    return jsonify([h.to_dict() for h in engine.heroes])


@app.route('/api/enemies', methods=['GET'])
def get_enemies():
    """Retorna todos los enemigos del combate actual."""
    return jsonify([e.to_dict() for e in engine.enemies])


@app.route('/api/skills', methods=['GET'])
def get_all_skills():
    """Retorna todas las habilidades disponibles."""
    return jsonify(ALL_SKILLS)


@app.route('/api/skills/<fighter_id>', methods=['GET'])
def get_fighter_skills(fighter_id: str):
    """Retorna las habilidades de un combatiente específico."""
    all_fighters = engine.heroes + engine.enemies
    fighter = next((f for f in all_fighters if str(f.id) == fighter_id), None)
    if not fighter:
        return jsonify({'error': 'Combatiente no encontrado'}), 404
    skills = get_skills_for(fighter.skill_ids)
    # Agregar cooldown actual
    for skill in skills:
        skill['current_cooldown'] = fighter.get_cooldown(skill['id'])
        skill['can_use'] = (
            fighter.current_mp >= skill['mp_cost'] and
            fighter.get_cooldown(skill['id']) == 0
        )
    return jsonify(skills)


@app.route('/api/difficulty', methods=['POST'])
def set_difficulty():
    """Cambia la dificultad del combate."""
    data = request.get_json() or {}
    difficulty = data.get('difficulty', 'normal')
    if difficulty not in ('easy', 'normal', 'hard'):
        return jsonify({'error': 'Dificultad inválida'}), 400
    engine.difficulty = difficulty
    return jsonify({'success': True, 'difficulty': difficulty})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("  SAINT SEIYA - BATTLE DEMO")
    print(f"  Servidor iniciado en: http://localhost:{port}")
    print("=" * 60)
    app.run(debug=False, port=port, host='0.0.0.0')
