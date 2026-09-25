
# Technical Brief — Ladle Refractory Thermal Integrity Monitor

**Author:** Altug Remzi Akay

**Version:** 1.0

**Date:** September 2026

This document presents the engineering methodology behind the Process
Intensity model for predicting ladle refractory wear.

---

## 1. Motivation

The MIA 2025-140 incident at Ovako Smedjebacken showed that static
**Time in Ladle** metrics fail to capture the true drivers of refractory degradation. A ladle that has accumulated 200 minutes of "quiet" holding time may be in better condition than a ladle that has seen only 60 minutes of aggressive vacuum treatment.

The Process Intensity model treats each minute of ladle service as
**weighted** by the chemical and kinetic stress it produces. The result is a physically grounded risk score that can be thresholded into actionable control commands.

---

## 2. Thermodynamic Foundation

### 2.1 The Dominant Exothermic Reactions

At the slag-metal interface, two reactions dominate the exothermic energy budget:

**Silicon oxidation:**

$$
\text{Si} + \text{O}_2 \rightarrow \text{SiO}_2 \qquad \Delta H^0 = -911 \text{ kJ/mol}
$$

Normalized per gram of Si (molar mass 28.09 g/mol):

$$
\Delta h_{\text{Si}} = \frac{911}{28.09} = 32.43 \text{ kJ/g}
$$

**Aluminum oxidation:**

$$
2\text{Al} + \tfrac{3}{2}\text{O}_2 \rightarrow \text{Al}_2\text{O}_3 \qquad \Delta H^0 = -1675 \text{ kJ/mol (per 2 mol Al)}
$$

Normalized per gram of Al (molar mass 26.98 g/mol):

$$
\Delta h_{\text{Al}} = \frac{1675}{2 \times 26.98} = 31.04 \text{ kJ/g}
$$

These values are consistent with the CRC Handbook of Chemistry and Physics and the NIST-JANAF Thermochemical Tables.

### 2.2 Exothermic Energy per Tonne

For a steel heat with Si-Jump $f_{\text{Si}}$ and Al-Consumed $f_{\text{Al}}$
(both expressed as mass fractions), the total exothermic energy released per tonne of steel is:

$$
E_{\text{exo}} = 10^6 \left( f_{\text{Si}} \cdot \Delta h_{\text{Si}} + f_{\text{Al}} \cdot \Delta h_{\text{Al}} \right) \quad [\text{kJ/t}]
$$

**Worked example:** Si-Jump = 0.26%, Al = 0.172%

$$
E_{\text{exo}} = 10^6 (0.0026 \times 32.43 + 0.00172 \times 31.04) = 137{,}707 \text{ kJ/t}
$$

### 2.3 Normalization

To keep the intensity value in a convenient numerical range, we normalize by a reference energy of 100,000 kJ/t:

$$
\Delta = \frac{E_{\text{exo}}}{100{,}000}
$$

The example above gives $\Delta = 1.377$.

---

## 3. Kinetic Amplification

### 3.1 Vacuum Treatment

Vacuum degassing (VTD) subjects the refractory wall to:

- **Turbulent shear** from argon bubbling
- **Thermal cycling** during pressure swings
- **Chemical attack** from slag-metal reactions accelerated by the vacuum

The **process intensity factor** captures this amplification:

$$
\text{IF}(t_{\text{VTD}}) =
\begin{cases}
1 & \text{if } t_{\text{VTD}} \leq t_c \\
1 + \dfrac{t_{\text{VTD}} - t_c}{t_c} & \text{if } t_{\text{VTD}} > t_c
\end{cases}
$$

where $t_c = 20$ minutes is the **critical vacuum duration** established from operational experience.

### 3.2 Binary Mapping

The historical CSV logs VTD treatment as a binary flag (1 = yes, 0 = no). For the model, we map:

| Flag | Nominal Duration |
|------|------------------|
| 0 | 0 min |
| 1 | 25 min |

A duration of 25 min yields $\text{IF} = 1.25$, i.e. **25% faster wear** than a non-VTD heat of the same chemistry.

---

## 4. Decision Logic

The model issues one of three control commands:

| Status | Condition | Recommended Action |
|--------|-----------|-------------------|
| 🟢 **NORMAL** | $\Delta \leq 1.35$ | Standard operational turnaround |
| 🟡 **YELLOW** | $1.35 < \Delta \leq 1.65$ | Focused post-cast visual inspection |
| 🔴 **RED** | $\Delta > 1.65$ **AND** $t_{\text{VTD}} > 20$ min | Remove from cycle; dust blow-off; technical verification |

### 4.1 Calibration Procedure

The thresholds were calibrated against the MIA 2025-140 dataset using the following procedure:

1. Compute $\Delta$ for every historical heat.
2. Sort by descending $\Delta$.
3. Set the YELLOW threshold at the **median of the upper quartile**.
4. Set the RED threshold at the **95th percentile of the non-VTD subset**.

This produced:

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| YELLOW | 1.35 | Above this level, chemical stress exceeds the mean by >1σ |
| RED | 1.65 | Corresponds to the top 10% of heats even without VTD |
| Critical VTD | 20 min | Empirically determined from successful relining intervals |

---

## 5. Case Study — MIA 2025-140

Ladle 22 experienced sudden shell overheating during a casting sequence. The static *Time in Ladle* metric was well within nominal limits, and the shell dust layer masked the thermal signature from the camera.

Applying the Process Intensity model retroactively to the recorded data:

| Parameter | Value |
|-----------|-------|
| Si-Jump | 0.34% |
| Al-Consumed | 0.28% |
| VTD | Yes (≈25 min) |
| **Exothermic Delta** | **1.88** |
| **Status** | 🔴 **RED** |

The model would have flagged Ladle 22 for **immediate removal from the active cycle** — hours before the shell overheating occurred. This is the concrete value proposition of the tool.

---

## 6. Implementation Notes

- **Language:** Python 3.10+
- **Dependencies:** `pandas`, `numpy`, `matplotlib`, `streamlit`
- **Architecture:** See `README.md`, Section 4
- **Tests:** `tests/test_physics.py` covers both the legacy empirical model and the thermodynamic model

### 6.1 Design Decisions

| Decision | Rationale |
|----------|-----------|
| Normalize by 100,000 kJ/t | Convenient range for thresholds and display |
| Linear intensity factor above $t_c$ | Simplest defensible model; extends naturally to higher-order kinetics |
| Separate YELLOW and RED thresholds | Matches industry practice (Observation → Control) |
| Binary VTD mapping | Sufficient for the current dataset; extend to real durations when available |

---

## 7. Limitations

1. **No thermal field model.** The model predicts *risk*, not actual shell temperature.
2. **No refractory age tracking.** Wear accumulates over the ladle lifetime; the current model evaluates each heat independently.
3. **No slag composition.** Future versions could include slag basicity and FeO content.
4. **Empirical thresholds.** Recalibrate for other steel plants or ladle geometries.
5. **No real-time data integration.** The current version reads a static CSV.

---

## 8. Future Work

- [ ] **Slag composition inputs** (basicity, FeO, MnO)
- [ ] **Refractory age tracking** (cumulative heat counter)
- [ ] **PINN residual layer** to learn calibration offsets from measured shell temperatures
- [ ] **Real-time OPC-UA data adapter** for plant integration
- [ ] **Predictive remaining useful life (RUL)** as a function of future heat schedules

---

## 9. References

1. **MIA 2025-140 incident report**, Ovako Smedjebacken, 2025.
2. **CRC Handbook of Chemistry and Physics**, 100th ed., CRC Press.
3. **NIST-JANAF Thermochemical Tables**, 4th ed., 1998.
4. **SINTEF ladle refractory model**, Internal presentation, 2024.
5. **ASM Metals Handbook**, Vol. 1: Properties and Selection.

---

## 10. Contact

**Altug Remzi Akay**

Email: altug.akay@bergsskolan.se

GitHub: [@altugrakay-commits](https://github.com/altugrakay-commits)