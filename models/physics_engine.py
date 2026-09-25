"""
physics_engine.py — Refractory wear prediction model
====================================================
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

# Thermodynamic constants (kJ per gram of element oxidized)
DELTA_H_SI_KJ_PER_G = -32.43
DELTA_H_AL_KJ_PER_G = -31.04

# Normalization reference: 100,000 kJ/t
ENERGY_REFERENCE_KJ_PER_TONNE = 100_000.0


class OperationalStatus(Enum):
    NORMAL = "NORMAL"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass(frozen=True)
class ThresholdConfig:
    yellow_limit: float = 0.45
    red_limit: float = 0.55
    critical_vtd_time_min: float = 20.0


class RefractoryWearModel:

    def __init__(
        self,
        k1: Optional[float] = None,
        k2: Optional[float] = None,
        yellow_limit: float = 0.45,
        red_limit: float = 0.55,
        critical_vtd_time: float = 20.0,
    ):
        self.delta_H_Si = abs(DELTA_H_SI_KJ_PER_G)
        self.delta_H_Al = abs(DELTA_H_AL_KJ_PER_G)
        self.k1 = k1
        self.k2 = k2
        self.yellow_limit = yellow_limit
        self.red_limit = red_limit
        self.critical_vtd_time = critical_vtd_time

    # --- Layer 1: Thermodynamics -----------------------------------------

    def calculate_exothermic_energy_kJ_per_t(
        self,
        si_jump_fraction: float,
        al_consumed_fraction: float,
    ) -> float:
        si_grams = si_jump_fraction * 1e6
        al_grams = al_consumed_fraction * 1e6
        energy_si = si_grams * self.delta_H_Si
        energy_al = al_grams * self.delta_H_Al
        return energy_si + energy_al

    def calculate_exothermic_delta(
        self,
        delta_si: float,
        delta_al: float,
    ) -> float:
        if self.k1 is not None and self.k2 is not None:
            return (delta_si * self.k1) + (delta_al * self.k2)
        energy = self.calculate_exothermic_energy_kJ_per_t(delta_si, delta_al)
        return energy / ENERGY_REFERENCE_KJ_PER_TONNE

    # --- Layer 2: Kinetics -----------------------------------------------

    def process_intensity_factor(self, vtd_time_min: float) -> float:
        if vtd_time_min <= self.critical_vtd_time:
            return 1.0
        excess = vtd_time_min - self.critical_vtd_time
        return 1.0 + excess / self.critical_vtd_time

    # --- Layer 3: Decision -----------------------------------------------

    def evaluate_operational_status(
        self,
        exothermal_delta: float,
        vtd_time_min: float,
    ) -> str:
        if (
            exothermal_delta > self.red_limit
            and vtd_time_min > self.critical_vtd_time
        ):
            return OperationalStatus.RED.value
        elif exothermal_delta > self.yellow_limit:
            return OperationalStatus.YELLOW.value
        else:
            return OperationalStatus.NORMAL.value

    # --- Convenience -----------------------------------------------------

    def evaluate(
        self,
        si_jump_fraction: float,
        al_consumed_fraction: float,
        vtd_time_min: float,
    ) -> dict:
        energy = self.calculate_exothermic_energy_kJ_per_t(
            si_jump_fraction, al_consumed_fraction
        )
        delta = self.calculate_exothermic_delta(
            si_jump_fraction, al_consumed_fraction
        )
        intensity_factor = self.process_intensity_factor(vtd_time_min)
        status = self.evaluate_operational_status(delta, vtd_time_min)

        return {
            "si_jump_fraction": si_jump_fraction,
            "al_consumed_fraction": al_consumed_fraction,
            "exothermic_energy_kJ_per_t": energy,
            "exothermic_delta": delta,
            "vtd_time_min": vtd_time_min,
            "intensity_factor": intensity_factor,
            "status": status,
        }