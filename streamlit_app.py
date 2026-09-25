"""
streamlit_app.py — Ladle Refractory Thermal Integrity Monitor
==============================================================
"""

import io
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from config import (
    DATA_PATH,
    YELLOW_LIMIT,
    RED_LIMIT,
    CRITICAL_VTD_TIME_MIN,
    VTD_TIME_IF_YES_MIN,
    VTD_TIME_IF_NO_MIN,
)
from models.physics_engine import RefractoryWearModel, OperationalStatus


# ============================================================================
# 0. PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Ladle Refractory Monitor",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Ladle Refractory Thermal Integrity Monitor")
st.markdown(
    "**Process Intensity model** — Moving beyond static *Time in Ladle* "
    "metrics by tracking **thermodynamic chemical stress** and "
    "**kinetic stirring erosion** simultaneously."
)

# ============================================================================
# 1. INITIALIZE MODEL
# ============================================================================

model = RefractoryWearModel(
    yellow_limit=YELLOW_LIMIT,
    red_limit=RED_LIMIT,
    critical_vtd_time=CRITICAL_VTD_TIME_MIN,
)

# ============================================================================
# 2. SIDEBAR - SINGLE HEAT INPUT
# ============================================================================

with st.sidebar:
    st.header("⚙️ Single Heat Evaluation")

    si_jump = st.number_input(
        "Si-Jump (%)", min_value=0.0, max_value=2.0,
        value=0.26, step=0.01, format="%.3f",
    )
    al_consumed = st.number_input(
        "Al-Consumed (%)", min_value=0.0, max_value=2.0,
        value=0.172, step=0.01, format="%.3f",
    )
    vtd_flag = st.selectbox("VTD Treatment", ["No (0)", "Yes (1)"])
    vtd_time = (
        VTD_TIME_IF_YES_MIN if vtd_flag.startswith("Yes")
        else VTD_TIME_IF_NO_MIN
    )

    st.markdown("---")
    st.caption(
        f"**Model thresholds:**\n\n"
        f"- YELLOW when Δ > {YELLOW_LIMIT}\n\n"
        f"- RED when Δ > {RED_LIMIT} **and** VTD > {CRITICAL_VTD_TIME_MIN} min\n\n"
        f"- Reference scale: Δ = 1.0 ↔ 100,000 kJ/t"
    )

# ============================================================================
# 3. SINGLE HEAT RESULT
# ============================================================================

st.header("🔍 Single Heat Evaluation")

result = model.evaluate(
    si_jump_fraction=si_jump / 100.0,
    al_consumed_fraction=al_consumed / 100.0,
    vtd_time_min=vtd_time,
)

status = result["status"]
if status == OperationalStatus.NORMAL.value:
    st.success("🟢 **NORMAL** — Nominal cycle, resume standard operations.")
elif status == OperationalStatus.YELLOW.value:
    st.warning("🟡 **YELLOW** — Execute focused post-cast visual refractory check.")
else:
    st.error("🔴 **RED** — Remove from cycle. Run dust blow-off & technical verification.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Exothermic Energy", f"{result['exothermic_energy_kJ_per_t']:,.0f} kJ/t")
with col2:
    st.metric("Exothermic Delta (Δ)", f"{result['exothermic_delta']:.3f}")
with col3:
    st.metric("Intensity Factor", f"{result['intensity_factor']:.3f}×")
with col4:
    st.metric("VTD Duration", f"{result['vtd_time_min']:.1f} min")

# ============================================================================
# 4. BATCH ANALYSIS
# ============================================================================

st.header("📊 Batch Analysis")

# --- Data source selection ---------------------------------------------------
with st.expander("📁 Data Source", expanded=False):
    use_bundled = st.checkbox("Use bundled ladle_analysis.csv", value=True)
    uploaded = None if use_bundled else st.file_uploader("Upload CSV", type=["csv"])


# --- Robust column finder ----------------------------------------------------
def _find_column(df: pd.DataFrame, candidates: list) -> str:
    """Return the first column name from candidates that exists in df.
    Case-insensitive and strips whitespace from both sides."""
    norm_cols = {c.strip().lower(): c for c in df.columns}
    for name in candidates:
        key = name.strip().lower()
        if key in norm_cols:
            return norm_cols[key]
    raise KeyError(f"None of {candidates} found in {list(df.columns)}")


# --- Robust loader -----------------------------------------------------------
def load_ladle_data() -> pd.DataFrame | None:
    """Load the bundled ladle_analysis.csv (semicolon separator, comma decimal)."""
    path = Path(DATA_PATH)
    if not path.exists():
        st.error(f"❌ Data file not found: {path}")
        return None

    try:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(path, sep=";", decimal=",", encoding="latin-1")
        except Exception as e:
            st.error(f"❌ Failed to read CSV: {e}")
            return None
    except Exception as e:
        st.error(f"❌ Failed to read CSV: {e}")
        return None

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    # Drop blank separator rows
    df = df.dropna(subset=["Last Heat ID"]).reset_index(drop=True)
    return df


# --- Batch evaluation --------------------------------------------------------
def evaluate_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Run the model over every row with robust column matching."""
    expected_columns = [
        "Heat ID", "Si-Jump (%)", "Al-Consumed (%)",
        "Exothermic (kJ/t)", "Delta (Δ)", "VTD (min)",
        "Status", "Slag Health",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=expected_columns)

    # --- Resolve actual column names (case-insensitive) ---
    try:
        col_heat = _find_column(df, ["Last Heat ID", "Last_Heat_ID", "Heat ID"])
        col_si   = _find_column(df, ["Si-Jump", "Si_Jumps", "Si Jump"])
        col_al   = _find_column(df, ["Al-Consumed", "Al_Consumed", "Al Consumed"])
        col_vtd  = _find_column(df, ["VTD Treatment (Y/N)", "VTD_Treatment_(Y/N)",
                                     "VTD Treatment", "VTD"])
    except KeyError as e:
        st.error(f"❌ Missing required column: {e}")
        st.info(f"Available columns: {list(df.columns)}")
        return pd.DataFrame(columns=expected_columns)

    col_slag = None
    for name in ["Slag Line Health Index", "Slag_Line_Health_Index"]:
        try:
            col_slag = _find_column(df, [name])
            break
        except KeyError:
            continue

    # --- Process each row ---
    rows = []
    for _, row in df.iterrows():
        try:
            si = float(row[col_si]) / 100.0
            al = float(row[col_al]) / 100.0
            vtd_flag = int(row[col_vtd])
            vtd_time = (
                VTD_TIME_IF_YES_MIN if vtd_flag == 1
                else VTD_TIME_IF_NO_MIN
            )
            res = model.evaluate(si, al, vtd_time)
            rows.append({
                "Heat ID": row[col_heat],
                "Si-Jump (%)": round(si * 100, 3),
                "Al-Consumed (%)": round(al * 100, 3),
                "Exothermic (kJ/t)": round(res["exothermic_energy_kJ_per_t"], 0),
                "Delta (Δ)": round(res["exothermic_delta"], 3),
                "VTD (min)": vtd_time,
                "Status": res["status"],
                "Slag Health": (
                    row[col_slag] if col_slag else np.nan
                ),
            })
        except Exception as e:
            st.warning(f"Skipping row {row.get(col_heat, '?')}: {e}")
            continue

    if not rows:
        st.warning("⚠️ No valid rows could be processed. Check your CSV format.")
        return pd.DataFrame(columns=expected_columns)

    return pd.DataFrame(rows)


# --- Load the data -----------------------------------------------------------
if use_bundled:
    df_raw = load_ladle_data()
elif uploaded is not None:
    try:
        df_raw = pd.read_csv(uploaded, sep=";", decimal=",")
        df_raw.columns = df_raw.columns.str.strip()
        df_raw = df_raw.dropna(subset=["Last Heat ID"]).reset_index(drop=True)
    except Exception as e:
        st.error(f"Could not parse uploaded file: {e}")
        df_raw = None
else:
    df_raw = None


# --- Render results ----------------------------------------------------------
if df_raw is not None:
    df_results = evaluate_batch(df_raw)

    if df_results.empty:
        st.warning("⚠️ No valid heat records were parsed. Nothing to display.")
    else:
        col_a, col_b = st.columns([1, 2])

        with col_a:
            st.subheader("Status Counts")
            counts = df_results["Status"].value_counts()
            for label in ["NORMAL", "YELLOW", "RED"]:
                n = int(counts.get(label, 0))
                st.metric(label, n)

        with col_b:
            st.subheader("Exothermic Delta Distribution")
            fig, ax = plt.subplots(figsize=(8, 4))
            colours = df_results["Status"].map({
                "NORMAL": "#2ecc71",
                "YELLOW": "#f39c12",
                "RED": "#e74c3c",
            })
            ax.bar(range(len(df_results)), df_results["Delta (Δ)"], color=colours)
            ax.axhline(YELLOW_LIMIT, color="#f39c12", linestyle="--",
                       label=f"YELLOW limit ({YELLOW_LIMIT})")
            ax.axhline(RED_LIMIT, color="#e74c3c", linestyle="--",
                       label=f"RED limit ({RED_LIMIT})")
            ax.set_xticks(range(len(df_results)))
            ax.set_xticklabels(df_results["Heat ID"], rotation=90, fontsize=8)
            ax.set_ylabel("Exothermic Delta (Δ)")
            ax.set_title("Chemical Stress per Heat")
            ax.legend()
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        # Full results table
        st.subheader("Full Results")
        st.dataframe(df_results, use_container_width=True)

        # Download
        csv_bytes = df_results.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Results (CSV)",
            data=csv_bytes,
            file_name="ladle_refractory_results.csv",
            mime="text/csv",
        )

        # Chemistry space
        st.subheader("Chemistry Space")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        for label, colour in [("NORMAL", "#2ecc71"),
                              ("YELLOW", "#f39c12"),
                              ("RED", "#e74c3c")]:
            subset = df_results[df_results["Status"] == label]
            if not subset.empty:
                ax2.scatter(
                    subset["Si-Jump (%)"], subset["Al-Consumed (%)"],
                    c=colour, s=80, label=label, alpha=0.75,
                    edgecolors="black",
                )
        ax2.set_xlabel("Si-Jump (%)")
        ax2.set_ylabel("Al-Consumed (%)")
        ax2.set_title("Heat Chemistry Coloured by Status")
        ax2.legend()
        ax2.grid(True, linestyle=":", alpha=0.5)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

# ============================================================================
# 5. FOOTER
# ============================================================================

st.markdown("---")
st.caption(
    "**Ladle Refractory Monitor** · Process Intensity Model v1.0 · "
    "Developed for Ovako Smedjebacken · Based on MIA 2025-140 incident · "
    "See [TECHNICAL_BRIEF.md](TECHNICAL_BRIEF.md) for the engineering derivation."
)