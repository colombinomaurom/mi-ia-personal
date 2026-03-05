"""
Módulo de base de datos - Gestiona la carga y almacenamiento de héroes y enemigos.
Usa SQLite para persistencia y JSON para datos iniciales.
"""
import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'game.db')
HEROES_JSON = os.path.join(BASE_DIR, 'heroes.json')
ENEMIES_JSON = os.path.join(BASE_DIR, 'enemies.json')


def get_connection():
    """Retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa la base de datos y carga datos desde JSON si está vacía."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heroes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            title TEXT,
            icon TEXT,
            element TEXT,
            team TEXT DEFAULT 'hero',
            level INTEGER DEFAULT 1,
            hp INTEGER,
            mp INTEGER,
            atk INTEGER,
            def_stat INTEGER,
            spd INTEGER,
            crit_rate INTEGER,
            crit_dmg INTEGER,
            dodge INTEGER,
            skills TEXT,
            passive TEXT,
            synergy_tags TEXT,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            title TEXT,
            icon TEXT,
            element TEXT,
            team TEXT DEFAULT 'enemy',
            level INTEGER DEFAULT 1,
            hp INTEGER,
            mp INTEGER,
            atk INTEGER,
            def_stat INTEGER,
            spd INTEGER,
            crit_rate INTEGER,
            crit_dmg INTEGER,
            dodge INTEGER,
            skills TEXT,
            passive TEXT,
            ai_style TEXT,
            synergy_tags TEXT,
            description TEXT
        )
    ''')
    conn.commit()

    # Cargar héroes desde JSON si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM heroes')
    if cursor.fetchone()[0] == 0:
        with open(HEROES_JSON, 'r', encoding='utf-8') as f:
            heroes = json.load(f)
        for h in heroes:
            cursor.execute('''
                INSERT INTO heroes (id, name, title, icon, element, team, level,
                    hp, mp, atk, def_stat, spd, crit_rate, crit_dmg, dodge,
                    skills, passive, synergy_tags, description)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                h['id'], h['name'], h['title'], h['icon'], h['element'],
                h['team'], h['level'], h['hp'], h['mp'], h['atk'],
                h['def'], h['spd'], h['crit_rate'], h['crit_dmg'],
                h['dodge'], json.dumps(h['skills']), h['passive'],
                json.dumps(h['synergy_tags']), h['description']
            ))

    # Cargar enemigos desde JSON si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM enemies')
    if cursor.fetchone()[0] == 0:
        with open(ENEMIES_JSON, 'r', encoding='utf-8') as f:
            enemies = json.load(f)
        for e in enemies:
            cursor.execute('''
                INSERT INTO enemies (id, name, title, icon, element, team, level,
                    hp, mp, atk, def_stat, spd, crit_rate, crit_dmg, dodge,
                    skills, passive, ai_style, synergy_tags, description)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                e['id'], e['name'], e['title'], e['icon'], e['element'],
                e['team'], e['level'], e['hp'], e['mp'], e['atk'],
                e['def'], e['spd'], e['crit_rate'], e['crit_dmg'],
                e['dodge'], json.dumps(e['skills']), e['passive'],
                e['ai_style'], json.dumps(e['synergy_tags']), e['description']
            ))

    conn.commit()
    conn.close()
    print("[DB] Base de datos inicializada correctamente.")


def load_all_heroes():
    """Carga todos los héroes desde la base de datos como diccionarios."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM heroes')
    rows = cursor.fetchall()
    conn.close()
    heroes = []
    for row in rows:
        h = dict(row)
        h['def'] = h.pop('def_stat')
        h['skills'] = json.loads(h['skills'])
        h['synergy_tags'] = json.loads(h['synergy_tags'])
        heroes.append(h)
    return heroes


def load_all_enemies():
    """Carga todos los enemigos desde la base de datos como diccionarios."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM enemies')
    rows = cursor.fetchall()
    conn.close()
    enemies = []
    for row in rows:
        e = dict(row)
        e['def'] = e.pop('def_stat')
        e['skills'] = json.loads(e['skills'])
        e['synergy_tags'] = json.loads(e['synergy_tags'])
        enemies.append(e)
    return enemies


if __name__ == '__main__':
    init_db()
    heroes = load_all_heroes()
    enemies = load_all_enemies()
    print(f"Héroes cargados: {[h['name'] for h in heroes]}")
    print(f"Enemigos cargados: {[e['name'] for e in enemies]}")
