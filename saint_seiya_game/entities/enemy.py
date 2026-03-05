"""
Módulo Enemy - Clase de enemigos controlados por la IA.
Extiende Fighter con mecánicas específicas de monstruos de calabozo.
"""
from .fighter import Fighter


class Enemy(Fighter):
    """Clase para enemigos controlados por la IA."""

    def __init__(self, data: dict):
        super().__init__(data)
        self.team = 'enemy'
        self.ai_style = data.get('ai_style', 'aggressive')

        # Estado IA
        self._berserk_triggered = False     # Para Minotauro: frenético con poca HP
        self._enrage_stack = 0              # Acumulación de furia

    def take_damage(self, damage: int, ignore_shield=False):
        """Al recibir daño, algunos enemigos se enfurecen."""
        actual = super().take_damage(damage, ignore_shield)

        # Pasiva Minotauro: Iron Hide - cuando hp < 50% gana buff de frenético
        if self.passive == 'iron_hide' and self.hp_percent < 50:
            if not self._berserk_triggered:
                self._berserk_triggered = True
                self.buffs['iron_hide_rage'] = {'atk': 0.15, 'def': 0.10, 'duration': 999}

        # Pasiva Quimera: Hybrid Fury - cada 25% HP perdido, +5% ATK
        if self.passive == 'hybrid_fury':
            new_stack = int((100 - self.hp_percent) / 25)
            if new_stack > self._enrage_stack:
                self._enrage_stack = new_stack
                self.buffs['hybrid_fury'] = {'atk': 0.05 * new_stack, 'duration': 999}

        # Pasiva Medusa: Stone Curse - cuando aplica petrificación dura +1 turno
        # (manejado en effects.py)

        return actual

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['ai_style'] = self.ai_style
        return d
