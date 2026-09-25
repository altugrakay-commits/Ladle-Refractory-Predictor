# tests/test_physics.py
import unittest
from models.physics_engine import (
    RefractoryWearModel,
    OperationalStatus,
    DELTA_H_SI_KJ_PER_G,
    DELTA_H_AL_KJ_PER_G,
)


class TestThermodynamicModel(unittest.TestCase):
    """Test the thermodynamically grounded model (k1 = k2 = None)."""

    def setUp(self):
        self.model = RefractoryWearModel(
            yellow_limit=1.35,
            red_limit=1.65,
            critical_vtd_time=20.0,
        )

    # --- Energy calculations ---------------------------------------------

    def test_exothermic_energy_si_only(self):
        # 0.26% Si = 0.0026 fraction → 2600 g/t × 32.43 kJ/g = 84,318 kJ/t
        energy = self.model.calculate_exothermic_energy_kJ_per_t(0.0026, 0.0)
        self.assertAlmostEqual(energy, 2600 * 32.43, places=1)

    def test_exothermic_energy_al_only(self):
        # 0.20% Al = 0.0020 fraction → 2000 g/t × 31.04 kJ/g = 62,080 kJ/t
        energy = self.model.calculate_exothermic_energy_kJ_per_t(0.0, 0.0020)
        self.assertAlmostEqual(energy, 2000 * 31.04, places=1)

    def test_exothermic_energy_combined(self):
        # 0.26% Si + 0.20% Al → 84,318 + 62,080 = 146,398 kJ/t
        # FIXED: was calling calculate_exothermic_delta (normalized) instead
        #        of calculate_exothermic_energy_kJ_per_t (raw kJ/t).
        energy = self.model.calculate_exothermic_energy_kJ_per_t(0.0026, 0.0020)
        expected = 2600 * 32.43 + 2000 * 31.04
        self.assertAlmostEqual(energy, expected, places=1)

    def test_normalized_delta(self):
        delta = self.model.calculate_exothermic_delta(0.0026, 0.0020)
        # 146,398 / 100,000 = 1.464
        self.assertAlmostEqual(delta, 1.464, places=3)

    # --- Intensity factor ------------------------------------------------

    def test_intensity_factor_below_critical(self):
        self.assertEqual(self.model.process_intensity_factor(0.0), 1.0)
        self.assertEqual(self.model.process_intensity_factor(10.0), 1.0)
        self.assertEqual(self.model.process_intensity_factor(20.0), 1.0)

    def test_intensity_factor_above_critical(self):
        # 25 min with critical=20: 1 + (25-20)/20 = 1.25
        self.assertAlmostEqual(self.model.process_intensity_factor(25.0), 1.25)
        # 40 min: 1 + (40-20)/20 = 2.0
        self.assertAlmostEqual(self.model.process_intensity_factor(40.0), 2.0)

    # --- Status logic ----------------------------------------------------

    def test_status_normal(self):
        status = self.model.evaluate_operational_status(1.20, 25.0)
        self.assertEqual(status, OperationalStatus.NORMAL.value)

    def test_status_yellow(self):
        # Above yellow but below red
        status = self.model.evaluate_operational_status(1.50, 5.0)
        self.assertEqual(status, OperationalStatus.YELLOW.value)

    def test_status_red_requires_both_conditions(self):
        # High delta but low VTD → YELLOW
        status = self.model.evaluate_operational_status(1.80, 10.0)
        self.assertEqual(status, OperationalStatus.YELLOW.value)

        # High delta AND high VTD → RED
        status = self.model.evaluate_operational_status(1.80, 25.0)
        self.assertEqual(status, OperationalStatus.RED.value)

    # --- Full pipeline ---------------------------------------------------

    def test_full_evaluate_pipeline_yellow(self):
        """
        0.26% Si + 0.20% Al → Δ = 1.464, which is above YELLOW (1.35)
        but below RED (1.65), so the status is YELLOW regardless of VTD.
        FIXED: the previous version asserted RED, which was incorrect.
        """
        result = self.model.evaluate(0.0026, 0.0020, 25.0)
        self.assertEqual(result["status"], OperationalStatus.YELLOW.value)
        self.assertAlmostEqual(result["exothermic_delta"], 1.464, places=3)
        self.assertAlmostEqual(result["intensity_factor"], 1.25, places=3)

    def test_full_evaluate_pipeline_red(self):
        """
        0.32% Si + 0.28% Al → Δ ≈ 1.908, which exceeds RED (1.65).
        With VTD > 20 min, the status should be RED.
        """
        result = self.model.evaluate(0.0032, 0.0028, 25.0)
        self.assertEqual(result["status"], OperationalStatus.RED.value)
        self.assertGreater(result["exothermic_delta"], 1.65)


class TestLegacyModel(unittest.TestCase):
    """Test the legacy empirical model (k1, k2 supplied)."""

    def setUp(self):
        self.model = RefractoryWearModel(
            k1=0.8, k2=1.5,
            yellow_limit=0.45, red_limit=0.55,
            critical_vtd_time=20.0,
        )

    def test_legacy_delta(self):
        # (0.10 × 0.8) + (0.20 × 1.5) = 0.38
        result = self.model.calculate_exothermic_delta(0.10, 0.20)
        self.assertAlmostEqual(result, 0.38, places=3)

    def test_legacy_status_normal(self):
        self.assertEqual(
            self.model.evaluate_operational_status(0.30, 10.0),
            OperationalStatus.NORMAL.value,
        )

    def test_legacy_status_yellow(self):
        self.assertEqual(
            self.model.evaluate_operational_status(0.48, 10.0),
            OperationalStatus.YELLOW.value,
        )

    def test_legacy_status_red(self):
        self.assertEqual(
            self.model.evaluate_operational_status(0.58, 25.0),
            OperationalStatus.RED.value,
        )


if __name__ == "__main__":
    unittest.main()