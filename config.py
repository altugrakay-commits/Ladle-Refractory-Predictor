# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_PATH = os.path.join(DATA_DIR, "ladle_analysis.csv")

# ============================================================================
# MODEL SELECTION
# ============================================================================
# Setting K1 = K2 = None activates the thermodynamically grounded model,
# which uses the standard enthalpies of Si and Al oxidation instead of
# empirical coefficients.

K1 = None
K2 = None

# ============================================================================
# DYNAMIC WARNING THRESHOLDS
# ============================================================================
# These thresholds are calibrated for the thermodynamic (normalized) model.
# See TECHNICAL_BRIEF.md, Section 5, for the calibration procedure.
#
# Reference scale:
#     Δ = 1.0  →  100,000 kJ/t of exothermic energy released
#     Δ = 1.35 →  Observation trigger (YELLOW)
#     Δ = 1.65 →  Control trigger (RED, requires VTD > critical)
#
# Statistical distribution on the Ovako MIA 2025-140 dataset:
#     NORMAL (Δ < 1.35):  ~53% of heats
#     YELLOW (1.35 ≤ Δ < 1.65): ~27% of heats
#     RED (Δ ≥ 1.65 + VTD ≥ 20): ~20% of heats

YELLOW_LIMIT = 1.35
RED_LIMIT = 1.65
CRITICAL_VTD_TIME_MIN = 20.0

# ============================================================================
# VTD BINARY MAPPING
# ============================================================================
# The CSV records VTD treatment as a binary flag (1 = yes, 0 = no).
# We map it to a nominal duration for the kinetic model:

VTD_TIME_IF_YES_MIN = 25.0   # Assume 25 min of high-intensity vacuum stirring
VTD_TIME_IF_NO_MIN = 0.0     # No vacuum treatment