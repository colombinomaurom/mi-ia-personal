"""
Módulo Hero - Clase de héroes controlados por el jugador.
Extiende Fighter con mecánicas específicas de santos de bronce.
"""
from .fighter import Fighter


class Hero(Fighter):
    """Clase para héroes controlados por el jugador."""

    def __init__(self, data: dict):
        super().__init__(data)
        self.team = 'hero'

        # Mecánica de Cosmo (equivalente a rage/cosmo de Saint Seiya Awakening)
        self.cosmo = 0          # 0-100
        self.cosmo_max = 100

        # Pasivas especiales activadas
        self._passive_triggered = False

    def gain_cosmo(self, amount: int):
        """Gana Cosmo al recibir o dar daño."""
        self.cosmo = min(self.cosmo_max, self.cosmo + amount)

    def use_cosmo(self, amount: int) -> bool:
        if self.cosmo >= amount:
            self.cosmo -= amount
            return True
        return False

    def cosmo_burst_bonus(self) -> float:
        """Bono de Cosmo Burst: con cosmo lleno da +20% daño."""
        if self.cosmo >= 80:
            return 1.20
        elif self.cosmo >= 50:
            return 1.10
        return 1.0

    def take_damage(self, damage: int, ignore_shield=False):
        """Al recibir daño, gana Cosmo."""
        actual = super().take_damage(damage, ignore_shield)
        if actual > 0:
            cosmo_gain = max(3, int(actual / self.max_hp * 20))
            self.gain_cosmo(cosmo_gain)

        # Pasiva Shiryu: Dragon Scale - cuando hp < 30%, DEF aumenta 20%
        if self.passive == 'dragon_scale' and self.hp_percent < 30:
            if not self._passive_triggered:
                self._passive_triggered = True
                # Aplicar buff de DEF permanente para el combate
                self.buffs['dragon_scale'] = {'def': 0.20, 'duration': 999}

        return actual

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['cosmo'] = self.cosmo
        d['cosmo_max'] = self.cosmo_max
        d['cosmo_percent'] = round((self.cosmo / self.cosmo_max) * 100, 1)
        return d
