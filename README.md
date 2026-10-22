# Predictive Refractory Thermal Integrity & Wear Monitor
### Living Decision Support System (PoC Engine v1.0)
**Developed for Ovako Smedjebacken | Metallurgical Engineering LiA**

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live-red)](https://share.streamlit.io/user/altugrakay-commits)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Industrial Context & The Problem

In modern steelmaking, maintaining ladle structural integrity is paramount to operational safety and process efficiency. Traditionally, ladle refractory degradation is monitored using static, unweighted **"Time in Ladle"** metrics.

However, this paradigm failed during the **MIA 2025-140 incident** at Ovako Smedjebacken.

### The Catalyst Event (MIA 2025-140)

During a standard casting sequence, Ladle 22 experienced sudden shell overheating. The critical structural degradation occurred despite "Time in Ladle" metrics tracking safely within nominal operating limits.

| Project Metric | MIA 2025-140 Case Study Details |
| :--- | :--- |
| **Event** | Sudden shell overheating during casting sequence. |
| **Physical Barrier** | Heavy dust accumulation insulated the ladle shell, masking the visual thermal signature from sensors. |
| **Operational Logic** | System treated every operational minute as equal. |
| **Consequence** | High-risk emergency handling with breakout potential. |

### Root Cause Analysis

- **Methodological Blindspot:** Over-reliance on static, linear time metrics.
- **Process Dynamics:** Vacuum Degassing (VTD) processing time accelerates aggressive chemical refractory-slag kinetics.
- **Thermodynamics:** High-energy exothermic chemical reactions occur locally but are untracked by standard time limits.
- **Physical Interference:** Industrial dust blankets the steel shell's outer surface, shielding thermal cameras and manual laser thermometers from seeing localized hot spots.

**Core Thesis:** *We cannot treat every process minute as equal. Metallurgical processing intensity dictates that some minutes do five times more physical damage to refractory bricks than others.*

---

## 2. Physics-Based Solution: The Process Intensity Model

Instead of measuring static clock time, this system introduces **Process Intensity (I)** — a physically grounded risk score derived from the exothermic energy released at the slag–metal interface.

### 2.1 Thermodynamic Foundation

Two reactions dominate the exothermic energy budget:

- **Silicon oxidation:** Si + O₂ → SiO₂, ΔH⁰ = −911 kJ/mol → **32.43 kJ/g Si**
- **Aluminum oxidation:** 2Al + 1.5 O₂ → Al₂O₃, ΔH⁰ = −1675 kJ/mol → **31.04 kJ/g Al**

For a heat with mass fractions f_Si and f_Al:

$E_{\text{exo}} = 10^6 \left( f_{\text{Si}} \cdot 32.43 + f_{\text{Al}} \cdot 31.04 \right) \quad [\text{kJ/t}]$

### 2.2 Normalized Exothermic Delta

To keep the value in a convenient range, we normalize by **100,000 kJ/t**:

$$\Delta = \frac{E_{\text{exo}}}{100{,}000}$$

The sample heat (Si = 0.26%, Al = 0.172%) gives **Δ = 1.377**, which is the YELLOW level.

### 2.3 Kinetic Amplification (VTD)

Vacuum treatment amplifies wear via turbulent shear and thermal cycling:

$$\text{IF}(t_{\text{VTD}}) = \begin{cases} 1 & t_{\text{VTD}} \le 20 \\ 1 + \frac{t_{\text{VTD}} - 20}{20} & t_{\text{VTD}} > 20 \end{cases}$$

The binary VTD flag in the historical CSV is mapped to **0 min (no VTD)** or **25 min (VTD on)** → IF = 1.25×.

---

## 3. Decision Support Thresholds

| Status | Condition | Recommended Action |
|--------|-----------|-------------------|
| 🟢 **NORMAL** | Δ ≤ **1.35** | Standard operational turnaround |
| 🟡 **YELLOW** | 1.35 < Δ ≤ 1.65 | Focused post-cast visual refractory inspection |
| 🔴 **RED** | Δ > **1.65** **AND** VTD > 20 min | Remove from cycle; dust blow-off; technical verification |

### 3.1 Calibration

Thresholds were calibrated against the MIA 2025-140 dataset:

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| YELLOW | 1.35 | Chemical stress exceeds the mean by >1σ |
| RED | 1.65 | Top 10% of heats even without VTD |
| Critical VTD | 20 min | Empirically determined from relining intervals |

### 3.2 Retrospective Validation

Applying the model retroactively to the MIA 2025-140 data:

| Parameter | Value |
|-----------|-------|
| Si-Jump | 0.34% |
| Al-Consumed | 0.28% |
| VTD | Yes (≈25 min) |
| **Exothermic Delta** | **1.88** |
| **Status** | 🔴 **RED** |

The model would have flagged Ladle 22 for **immediate removal from the active cycle** — hours before the shell overheating occurred.

---

## 4. Repository Architecture

```
Ladle_Refractory_Predictor/
├── data/
│ └── ladle_analysis.csv # Historical heat data (15 heats from MIA 2025-140)
├── models/
│ └── physics_engine.py # RefractoryWearModel with thermodynamic constants
├── tests/
│ └── test_physics.py # 15 unit tests (all passing)
├── config.py # Thresholds, VTD mapping, data path
├── app.py # CLI dashboard
├── streamlit_app.py # Interactive web dashboard
├── requirements.txt
├── TECHNICAL_BRIEF.md # Full engineering derivation
├── README.md # This file
└── LICENSE
```

## 5. Getting Started

### Prerequisites

- Python 3.11+
- `pandas`, `numpy`, `matplotlib`, `streamlit`

### Installation

```bash
git clone https://github.com/altugrakay-commits/Ladle-Refractory-Predictor.git
cd Ladle-Refractory-Predictor
pip install -r requirements.txt
```

### Usage

#### Interactive web dashboard (recommended):
```bash
streamlit run streamlit_app.py
```
#### Command-line dashboard:
```bash
python app.py
```
#### Run unit test:
```bash
python -m unittest discover -s tests
```
#### Expected Output:

For a heat with Si = 0.26%, Al = 0.172%, no VTD:
 - Exothermic Energy: **137,707 kJ/t**
 - Exothermic Delta: **1.377**
 - Intensity Factor: **1.000×**
 - Status: 🟡 **YELLOW**

Batch analysis of the bundled dataset:
 - 8 NORMAL, 6 YELLOW, 1 RED

## 6. Dashboard Features

The Streamlit dashboard offers two modes:

**Single Heat Evaluation** — real-time status badge with thermodynamic breakdown

**Batch Analysis** — process the full CSV with:
 - Status counts (NORMAL / YELLOW / RED)
 - Bar chart of Δ per heat with threshold lines
 - Full results table with download button
 - Chemistry space scatter plot (Si vs Al, colored by status)

## 7. Engineering Deep Dive

For the full derivation, including calibration procedure, case study, and limitations, see TECHNICAL_BRIEF.md.

## 8. Roadmap

 - Slag composition inputs (basicity, FeO, MnO)
 - Refractory age tracking (cumulative heat counter)
 - PINN residual layer for calibration from shell temperature
 - Real-time OPC-UA data adapter for plant integration
 - Predictive remaining useful life (RUL)

## 9. License

This project is licensed under the MIT License — see LICENSE for details.

## 10. Contact

**Altug Remzi Akay** — Materials Technology Engineering, Bergsskolan

Email: altug.akay@bergsskolan.se

GitHub: @altugrakay-commits