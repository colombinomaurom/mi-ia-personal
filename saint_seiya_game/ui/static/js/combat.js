/* ============================================================
   SAINT SEIYA BATTLE DEMO – Combat Engine (Frontend)
   Gestiona la interfaz de combate, popups y flujo de turno.
   ============================================================ */

'use strict';

// ============================================================
// ESTADO GLOBAL DEL COMBATE
// ============================================================
const Game = {
  state: null,           // Estado completo del servidor
  selectedSkillId: null,
  selectedTargetId: null,
  currentHeroId: null,
  isProcessing: false,   // Evitar acciones dobles
  eventQueue: [],        // Cola de eventos para animaciones
  isAnimating: false,
  logHistory: [],        // Historial completo del log
};

// Delay configurable entre eventos
const EVENT_DELAY_MS  = 900;
const ENEMY_TURN_DELAY = 700;

// ============================================================
// COLORES ELEMENTALES
// ============================================================
const ELEMENT_COLORS = {
  light: '#ffd700', dark: '#9933ff', fire: '#ff5522',
  ice: '#44ccff', earth: '#88cc44', wind: '#44ffbb', neutral: '#888888'
};
const ELEMENT_ICONS = {
  light: '☀️', dark: '🌑', fire: '🔥',
  ice: '❄️', earth: '🌍', wind: '💨', neutral: '⚬'
};

// ============================================================
// INICIALIZACIÓN
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  loadCurrentState();
});

function loadCurrentState() {
  fetch('/api/state')
    .then(r => r.json())
    .then(state => {
      // Si no hay combate activo, iniciar uno
      if (!state.heroes || state.heroes.length === 0) {
        startBattle();
        return;
      }
      Game.state = state;
      renderAll();
      updateActionUI();
    })
    .catch(() => startBattle());
}

function startBattle() {
  fetch('/api/start_battle', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({difficulty: 'normal'})
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      Game.state = data.state;
      renderAll();
      // Si había eventos de turnos de enemigo iniciales, mostrarlos
      if (data.state.initial_enemy_events?.length) {
        queueEvents(data.state.initial_enemy_events);
      } else {
        updateActionUI();
      }
    }
  });
}

// ============================================================
// RENDER PRINCIPAL
// ============================================================
function renderAll() {
  if (!Game.state) return;
  renderEnemies();
  renderHeroes();
  renderBattleLog();
  renderTurnInfo();
  checkBattleEnd();
}

// ============================================================
// RENDER TARJETAS
// ============================================================
function renderEnemies() {
  const zone = document.getElementById('enemiesZone');
  zone.innerHTML = '';
  (Game.state.enemies || []).forEach(e => {
    zone.appendChild(createFighterCard(e, 'enemy'));
  });
}

function renderHeroes() {
  const zone = document.getElementById('heroesZone');
  zone.innerHTML = '';
  (Game.state.heroes || []).forEach(h => {
    zone.appendChild(createFighterCard(h, 'hero'));
  });
}

function createFighterCard(fighter, team) {
  const card = document.createElement('div');
  const isDead = !fighter.is_alive;
  const isCurrent = Game.state.current_fighter &&
                    Game.state.current_fighter.id === fighter.id;
  const isTarget = Game.selectedTargetId === fighter.id;

  card.className = `fighter-card ${team}-card ${isDead ? 'is-dead' : ''} ${isCurrent ? 'active-turn' : ''} ${isTarget ? 'selected-target' : ''}`;
  card.id = `card-${fighter.id}`;
  card.dataset.id = fighter.id;
  card.dataset.team = team;

  // HP bar color by percentage
  let hpColor = '#22cc44';
  if (fighter.hp_percent < 25) hpColor = '#cc2200';
  else if (fighter.hp_percent < 50) hpColor = '#cc8800';

  // Status effects icons
  const statusIcons = (fighter.status_effects || []).map(e => {
    return `<span class="status-icon" title="${e.name || e.type} (${e.duration} turnos)">${e.icon || '❓'}</span>`;
  }).join('');

  // Cosmo bar (only heroes)
  const cosmoBar = team === 'hero' ? `
    <div class="bar-row cosmo-row">
      <span class="bar-label" style="color:#cc8800;">Cos</span>
      <div class="stat-bar-container" style="height:5px;">
        <div class="stat-bar-fill cosmo-bar" style="width:${fighter.cosmo_percent || 0}%"></div>
      </div>
      <span class="bar-val" style="color:#cc8800; font-size:0.55em;">${fighter.cosmo || 0}</span>
    </div>` : '';

  // Escudo badge
  const shieldEffect = (fighter.status_effects || []).find(e => e.type === 'shield');
  const shieldBadge = shieldEffect ?
    `<div style="font-size:0.6em; color:#4488ff; margin-top:2px;">🛡️ ${shieldEffect.value}</div>` : '';

  card.innerHTML = `
    <div class="card-icon">${fighter.icon}</div>
    <div class="card-name">${fighter.name.split(' ')[0]}</div>
    <div class="card-title">${fighter.title || ''}</div>
    <div class="card-bars">
      <div class="bar-row">
        <span class="bar-label hp-text">HP</span>
        <div class="stat-bar-container hp-bar-container">
          <div class="stat-bar-fill hp-bar" style="width:${fighter.hp_percent}%; background: linear-gradient(90deg, #115522, ${hpColor});"></div>
        </div>
        <span class="bar-val hp-text">${fighter.current_hp}</span>
      </div>
      <div class="bar-row">
        <span class="bar-label mp-text">MP</span>
        <div class="stat-bar-container mp-bar-container">
          <div class="stat-bar-fill mp-bar" style="width:${fighter.mp_percent}%"></div>
        </div>
        <span class="bar-val mp-text">${fighter.current_mp}</span>
      </div>
      ${cosmoBar}
    </div>
    ${shieldBadge}
    <div class="card-status">${statusIcons}</div>
  `;

  // Click para seleccionar objetivo (en modo popup)
  if (team === 'enemy' && !isDead) {
    card.addEventListener('click', () => selectEnemyTarget(fighter.id));
  }

  return card;
}

// ============================================================
// RENDER LOG DE COMBATE
// ============================================================
function renderBattleLog() {
  const log = document.getElementById('battleLog');
  if (!Game.state.battle_log) return;

  // Agregar solo entradas nuevas
  const currentCount = log.children.length;
  const allEntries = Game.state.battle_log;

  // Limpiar y re-renderizar las últimas entradas
  log.innerHTML = '';
  allEntries.forEach(entry => {
    log.appendChild(createLogEntry(entry));
  });

  // Scroll al final
  log.scrollTop = log.scrollHeight;
}

function createLogEntry(entry) {
  const div = document.createElement('div');
  div.className = `log-entry type-${entry.type || 'info'}`;
  div.textContent = entry.message || '';
  return div;
}

function appendLogEntry(entry) {
  const log = document.getElementById('battleLog');
  const div = createLogEntry(entry);
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  Game.logHistory.push(entry);
}

// ============================================================
// RENDER INFO DE TURNO
// ============================================================
function renderTurnInfo() {
  const state = Game.state;
  const badge = document.getElementById('turnBadge');
  const info = document.getElementById('turnInfo');
  const miniOrder = document.getElementById('miniTurnOrder');

  if (!state) return;

  info.textContent = `Ronda ${state.turn_number || 1}`;

  if (state.current_fighter) {
    const isHero = state.current_fighter.team === 'hero';
    badge.textContent = isHero
      ? `⚡ ${state.current_fighter.name.split(' ')[0]}`
      : `👹 ${state.current_fighter.name.split(' ')[0]}`;
    badge.className = `current-turn-badge ${isHero ? 'hero-turn' : 'enemy-turn'}`;
  }

  // Mini orden de turnos
  if (state.turn_order) {
    miniOrder.innerHTML = state.turn_order.slice(0, 8).map((f, i) => {
      const style = i === 0 ? 'color:#ffd700; font-weight:bold;' : 'color:#666;';
      const icon = f.team === 'hero' ? '🔵' : '🔴';
      return `<div style="${style}">${icon} ${f.name.split(' ')[0]} (${f.spd})</div>`;
    }).join('');
  }
}

// ============================================================
// CONTROLES DE ACCIÓN
// ============================================================
function updateActionUI() {
  const state = Game.state;
  if (!state) return;

  const btnAttack = document.getElementById('btnAttack');
  const btnFlee = document.getElementById('btnFlee');
  const waiting = document.getElementById('waitingIndicator');
  const overlay = document.getElementById('actionOverlay');

  if (state.state === 'player_turn' && !Game.isProcessing) {
    btnAttack.disabled = false;
    btnFlee.disabled = false;
    waiting.classList.add('hidden');
    overlay.classList.remove('hidden');
    // Identificar el héroe en turno
    if (state.current_fighter && state.current_fighter.team === 'hero') {
      Game.currentHeroId = state.current_fighter.id;
    }
  } else {
    btnAttack.disabled = true;
    btnFlee.disabled = true;
    waiting.classList.remove('hidden');
  }

  // Ocultar overlay si el combate terminó
  if (['victory', 'defeat', 'flee'].includes(state.state)) {
    overlay.classList.add('hidden');
  }
}

// ============================================================
// POPUP DE HABILIDADES
// ============================================================
function openSkillPopup() {
  if (Game.isProcessing) return;
  if (!Game.currentHeroId) return;

  // Resetear selección
  Game.selectedSkillId = null;
  Game.selectedTargetId = null;

  // Encontrar héroe actual
  const hero = Game.state.heroes.find(h => h.id === Game.currentHeroId);
  if (!hero) return;

  // Llenar header del popup
  document.getElementById('popupHeroIcon').textContent = hero.icon;
  document.getElementById('popupHeroName').textContent = hero.name;
  document.getElementById('popupHpStat').textContent = `❤️ ${hero.current_hp}/${hero.max_hp}`;
  document.getElementById('popupMpStat').textContent = `💙 ${hero.current_mp}/${hero.max_mp}`;
  document.getElementById('popupCosmStat').textContent = `⭐ ${hero.cosmo || 0}/100`;
  document.getElementById('popupAtkStat').textContent = `⚔️ ATK ${hero.atk}`;

  // Cargar habilidades del héroe
  fetch(`/api/skills/${hero.id}`)
  .then(r => r.json())
  .then(skills => {
    renderSkillList(skills, hero);
    renderMiniEnemies();
    updatePopupStatus();
    document.getElementById('skillOverlay').classList.remove('hidden');
  });
}

function renderSkillList(skills, hero) {
  const list = document.getElementById('skillList');
  list.innerHTML = '';

  skills.forEach(skill => {
    const canUse = skill.can_use && hero.current_mp >= skill.mp_cost;
    const onCd = skill.current_cooldown > 0;
    const noMp = hero.current_mp < skill.mp_cost;

    const btn = document.createElement('button');
    btn.className = 'skill-btn';
    btn.disabled = !canUse;
    btn.dataset.skillId = skill.id;

    let statusText = '';
    if (onCd) statusText = `⏳ ${skill.current_cooldown} turnos`;
    else if (noMp) statusText = '⚡ Sin MP';

    const effectsText = [];
    if (skill.status_effect) {
      effectsText.push(`${skill.status_chance}% ${skill.status_effect} (${skill.status_duration}t)`);
    }
    if (skill.armor_pen > 0) {
      effectsText.push(`Penetra ${Math.round(skill.armor_pen * 100)}% DEF`);
    }
    if (skill.hits > 1) {
      effectsText.push(`${skill.hits} golpes`);
    }

    btn.innerHTML = `
      <div class="skill-icon-lg">${skill.icon || '⚔️'}</div>
      <div class="skill-info">
        <div class="skill-name">
          ${skill.name}
          ${skill.is_basic ? '<span class="basic-badge">Básico</span>' : ''}
        </div>
        <div class="skill-desc">${skill.description}</div>
        ${effectsText.length ? `<div class="skill-effects">${effectsText.join(' · ')}</div>` : ''}
        ${statusText ? `<div style="font-size:0.65em; color:#cc6655; margin-top:2px;">${statusText}</div>` : ''}
      </div>
      <div class="skill-cost">
        <div class="mp-cost">${skill.mp_cost > 0 ? `💙 ${skill.mp_cost}` : '🆓'}</div>
        ${skill.cooldown > 0 ? `<div class="cd-info">CD: ${skill.cooldown}</div>` : ''}
      </div>
    `;

    btn.addEventListener('click', () => selectSkill(skill, btn));
    list.appendChild(btn);
  });
}

function renderMiniEnemies() {
  const container = document.getElementById('miniEnemyList');
  container.innerHTML = '';

  (Game.state.enemies || []).forEach(e => {
    const div = document.createElement('div');
    div.className = `mini-enemy ${!e.is_alive ? 'mini-dead' : ''} ${Game.selectedTargetId === e.id ? 'mini-selected' : ''}`;
    div.dataset.id = e.id;

    const hpPct = e.hp_percent || 0;
    let hpColor = '#22cc44';
    if (hpPct < 25) hpColor = '#cc2200';
    else if (hpPct < 50) hpColor = '#cc8800';

    const statusIcons = (e.status_effects || []).map(s => s.icon || '').join('');

    div.innerHTML = `
      <div class="mini-enemy-icon">${e.icon}</div>
      <div class="mini-enemy-info">
        <div class="mini-name">${e.name.split(' ')[0]} ${statusIcons}</div>
        <div class="stat-bar-container" style="height:6px;">
          <div class="stat-bar-fill hp-bar"
               style="width:${hpPct}%; background: linear-gradient(90deg, #115522, ${hpColor});">
          </div>
        </div>
        <div style="font-size:0.6em; color:#777; margin-top:1px;">${e.current_hp}/${e.max_hp}</div>
      </div>
    `;

    if (e.is_alive) {
      div.addEventListener('click', () => selectTarget(e.id, div));
    }
    container.appendChild(div);
  });
}

function selectSkill(skill, btnEl) {
  // Deseleccionar anterior
  document.querySelectorAll('.skill-btn').forEach(b => b.classList.remove('selected'));
  btnEl.classList.add('selected');
  Game.selectedSkillId = skill.id;

  // Si la habilidad no necesita objetivo específico, auto-seleccionar
  const targetType = skill.target_type;
  if (['all_enemies', 'all_enemies_random', 'self', 'all_allies'].includes(targetType)) {
    Game.selectedTargetId = -1;
    document.querySelectorAll('.mini-enemy').forEach(e => e.classList.remove('mini-selected'));
  } else if (targetType === 'ally_lowest_hp') {
    Game.selectedTargetId = -1;
  }

  updatePopupStatus();
}

function selectTarget(targetId, divEl) {
  document.querySelectorAll('.mini-enemy').forEach(e => e.classList.remove('mini-selected'));
  divEl.classList.add('mini-selected');
  Game.selectedTargetId = targetId;
  updatePopupStatus();
}

function selectEnemyTarget(enemyId) {
  // Click en tarjeta de enemigo fuera del popup (para seleccionar objetivo)
  if (!Game.selectedSkillId) return;
  Game.selectedTargetId = enemyId;
  document.querySelectorAll('.fighter-card').forEach(c => c.classList.remove('selected-target'));
  const card = document.getElementById(`card-${enemyId}`);
  if (card) card.classList.add('selected-target');
  confirmSkill();
}

function updatePopupStatus() {
  const statusEl = document.getElementById('popupStatus');
  const confirmBtn = document.getElementById('btnConfirmSkill');

  if (!Game.selectedSkillId) {
    statusEl.textContent = 'Elige una habilidad y un objetivo';
    statusEl.className = 'popup-status';
    confirmBtn.disabled = true;
    return;
  }

  if (Game.selectedTargetId === null) {
    statusEl.textContent = '→ Elige un objetivo';
    statusEl.className = 'popup-status';
    confirmBtn.disabled = true;
    return;
  }

  statusEl.textContent = '✓ Listo para atacar!';
  statusEl.className = 'popup-status ready';
  confirmBtn.disabled = false;
}

function closeSkillPopup() {
  document.getElementById('skillOverlay').classList.add('hidden');
  Game.selectedSkillId = null;
  Game.selectedTargetId = null;
  // Limpiar selección visual
  document.querySelectorAll('.fighter-card').forEach(c => c.classList.remove('selected-target'));
}

// ============================================================
// CONFIRMAR Y ENVIAR ACCIÓN
// ============================================================
function confirmSkill() {
  if (!Game.selectedSkillId || Game.selectedTargetId === null) return;
  if (Game.isProcessing) return;

  closeSkillPopup();
  executeHeroAction(Game.currentHeroId, Game.selectedSkillId, Game.selectedTargetId);
}

function executeHeroAction(heroId, skillId, targetId) {
  Game.isProcessing = true;
  updateActionUI();

  fetch('/api/action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      hero_id: heroId,
      skill_id: skillId,
      target_id: targetId
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      console.error('Error:', data.error);
      Game.isProcessing = false;
      if (data.state) {
        Game.state = data.state;
        renderAll();
        updateActionUI();
      }
      return;
    }

    Game.state = data.state;

    // Procesar eventos con animación
    const events = data.events || [];
    queueEvents(events);
  })
  .catch(err => {
    console.error('Error de conexión:', err);
    Game.isProcessing = false;
    updateActionUI();
  });
}

// ============================================================
// COLA DE EVENTOS (ANIMACIONES SECUENCIALES)
// ============================================================
function queueEvents(events) {
  Game.eventQueue.push(...events);
  if (!Game.isAnimating) {
    processNextEvent();
  }
}

function processNextEvent() {
  if (Game.eventQueue.length === 0) {
    Game.isAnimating = false;
    // Actualizar todo al final de la cadena de eventos
    renderAll();
    updateActionUI();
    Game.isProcessing = false;
    return;
  }

  Game.isAnimating = true;
  const event = Game.eventQueue.shift();
  handleEvent(event);

  // Determinar delay según tipo de evento
  let delay = EVENT_DELAY_MS;
  if (['skill_used', 'new_round', 'synergy', 'battle_start'].includes(event.type)) {
    delay = 500;
  } else if (['death', 'victory', 'defeat'].includes(event.type)) {
    delay = 1200;
  } else if (['dot', 'status_applied', 'status_resisted'].includes(event.type)) {
    delay = 500;
  }

  setTimeout(processNextEvent, delay);
}

function handleEvent(event) {
  // Agregar al log
  if (event.message || event.type) {
    const formattedEvent = formatEvent(event);
    if (formattedEvent) {
      appendLogEntry({...event, message: formattedEvent});
    }
  }

  // Animaciones visuales
  switch (event.type) {
    case 'damage':
    case 'damage_summary':
      animateCard(event.target_id, 'damage-flash');
      if (event.is_crit) animateCard(event.target_id, 'crit-flash');
      updateCardHP(event.target_id, event.target_hp, event.target_max_hp);
      break;

    case 'heal':
      animateCard(event.target_id, 'heal-flash');
      updateCardHP(event.target_id, event.target_hp, event.target_max_hp);
      break;

    case 'death':
      animateCard(event.target_id, 'death-animation');
      setTimeout(() => {
        const card = document.getElementById(`card-${event.target_id}`);
        if (card) card.classList.add('is-dead');
      }, 400);
      break;

    case 'shield_applied':
      animateCard(event.target_id, 'heal-flash');
      break;

    case 'status_applied':
      animateCard(event.target_id, 'crit-flash');
      break;

    case 'dot':
      animateCard(getIdByName(event.target), 'damage-flash');
      break;

    case 'victory':
      setTimeout(() => showBattleEnd(true), 1000);
      break;

    case 'defeat':
      setTimeout(() => showBattleEnd(false), 1000);
      break;
  }
}

function formatEvent(event) {
  const t = event.type;

  if (t === 'damage') {
    const critStr = event.is_crit ? ' 💥CRÍTICO!' : '';
    return `${event.skill_icon || '⚔️'} ${event.attacker} → ${event.target}: ${event.damage} daño${critStr}`;
  }
  if (t === 'damage_summary') {
    const critsStr = event.crits > 0 ? ` (${event.crits} crítico!)` : '';
    return `${event.skill_icon || '⚔️'} ${event.attacker} → ${event.target}: ${event.damage} daño (${event.hits} golpes)${critsStr}`;
  }
  if (t === 'skill_used') {
    return `⚡ ${event.caster} usa ${event.skill_icon || ''} ${event.skill} [-${event.mp_cost}MP]`;
  }
  if (t === 'heal') {
    return `💚 ${event.caster} cura a ${event.target}: +${event.amount} HP`;
  }
  if (t === 'status_applied') {
    return `${event.icon || '❓'} ${event.target} recibe ${event.name || event.effect} (${event.duration}t)`;
  }
  if (t === 'status_resisted') {
    return `🛡️ ${event.target} resistió ${event.effect}`;
  }
  if (t === 'death') {
    return `💀 ${event.target} ha sido derrotado!`;
  }
  if (t === 'dot') {
    return `${event.icon || '🔥'} ${event.target} sufre ${event.damage} daño por ${event.effect}`;
  }
  if (t === 'shield_applied') {
    return `🛡️ ${event.target} recibe escudo de ${event.shield_value} HP`;
  }
  if (t === 'stunned') {
    return `🚫 ${event.fighter} no puede actuar (${event.effect})`;
  }
  if (t === 'dodge') {
    return `💨 ${event.target} esquivó el ataque!`;
  }
  if (t === 'new_round') {
    return `🔄 — Ronda ${event.turn || '?'} —`;
  }
  if (t === 'confusion_trigger') {
    return `🌀 ${event.message}`;
  }
  if (t === 'sleep_broken') {
    return `😲 ${event.message}`;
  }
  if (t === 'mp_drain') {
    return `💜 ${event.attacker} robó ${event.amount} MP a ${event.target}`;
  }
  if (t === 'effect_expired') {
    return `✨ ${event.target}: ${event.effect} expiró`;
  }
  if (t === 'flee') {
    return `🏃 Huyeron del combate...`;
  }
  if (event.message) return event.message;
  return null;
}

// ============================================================
// ANIMACIONES DE TARJETAS
// ============================================================
function animateCard(fighterId, animClass) {
  const card = document.getElementById(`card-${fighterId}`);
  if (!card) return;
  card.classList.remove(animClass);
  void card.offsetWidth; // Trigger reflow
  card.classList.add(animClass);
  setTimeout(() => card.classList.remove(animClass), 600);
}

function updateCardHP(fighterId, currentHp, maxHp) {
  const card = document.getElementById(`card-${fighterId}`);
  if (!card) return;

  const pct = maxHp > 0 ? (currentHp / maxHp) * 100 : 0;
  const bar = card.querySelector('.hp-bar');
  const hpVal = card.querySelector('.hp-text.bar-val');

  if (bar) bar.style.width = `${pct}%`;
  if (hpVal) hpVal.textContent = currentHp;
}

function getIdByName(name) {
  const all = [...(Game.state?.heroes || []), ...(Game.state?.enemies || [])];
  const f = all.find(x => x.name === name);
  return f ? f.id : null;
}

// ============================================================
// FIN DE COMBATE
// ============================================================
function checkBattleEnd() {
  if (!Game.state) return;
  if (Game.state.state === 'victory') showBattleEnd(true);
  else if (Game.state.state === 'defeat') showBattleEnd(false);
}

function showBattleEnd(isVictory) {
  const overlay = document.getElementById('battleEndOverlay');
  const box = document.getElementById('battleEndBox');
  const title = document.getElementById('endTitle');
  const subtitle = document.getElementById('endSubtitle');

  overlay.classList.remove('hidden');

  if (isVictory) {
    box.className = 'battle-end-box victory-box';
    title.className = 'end-title victory-title';
    title.textContent = '🏆 ¡VICTORIA!';
    subtitle.textContent = 'Los Santos de Bronce han triunfado sobre las fuerzas del Hades';
  } else {
    box.className = 'battle-end-box defeat-box';
    title.className = 'end-title defeat-title';
    title.textContent = '💀 DERROTA';
    subtitle.textContent = 'Los Santos han caído... el Hades ha ganado esta batalla';
  }
}

// ============================================================
// HUIR DEL COMBATE
// ============================================================
function fleeBattle() {
  if (!confirm('¿Estás seguro de que quieres huir del combate?')) return;

  fetch('/api/flee', { method: 'POST' })
  .then(r => r.json())
  .then(data => {
    appendLogEntry({type: 'flee', message: '🏃 Huyeron del combate...'});
    setTimeout(() => { window.location.href = '/'; }, 1500);
  });
}
