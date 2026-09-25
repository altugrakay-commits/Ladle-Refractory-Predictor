# app.py
import os
import pandas as pd
import config
from models.physics_engine import RefractoryWearModel

def print_dashboard_header():
    print("=" * 110)
    print("---OVAKO SMEDJEBACKEN - REFRACTORY THERMAL INTEGRITY & RECOVERY MONITOR---")
    print("---Living Decision Support System (PoC Engine v1.0)---")
    print("=" * 110)
    print(f"{'HEAT ID':<10} | {'Si Jump (%)':<12} | {'Al Cons (%)':<12} | {'Exo Delta':<10} | {'VTD Min':<8} | {'Status':<10} | {'Action Required'}")
    print("-" * 110)

def main():
    # Initialize the calibrated physical engine.
    model = RefractoryWearModel(
        k1 = config.K1,
        k2 = config.K2,
        yellow_limit=config.YELLOW_LIMIT,
        red_limit=config.RED_LIMIT,
        critical_vtd_time=config.CRITICAL_VTD_TIME_MIN
    )

    # Checks for the data file.
    if not os.path.exists(config.DATA_PATH):
        print(f"Error: Missing historical heat data file at: {config.DATA_PATH}")
        print("Please create the 'data/' folder and insert 'ladle_analysis.csv' to run the pipeline.")
        return
    
    # Ingests active process logs. 
    # ADDED: decimal=',' to both parsers to automatically convert "0,26" to 0.26
    try:
        df = pd.read_csv(config.DATA_PATH, encoding='latin-1', sep=',', decimal=',')
    except pd.errors.ParserError:
        try:
            df = pd.read_csv(config.DATA_PATH, encoding='latin-1', sep=';', decimal=',')
        except Exception as e:
            print(f"Error parsing CSV file: {e}")
            return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Clean up entirely empty rows (such as the second row ',,,,,,') 
    df = df.dropna(subset=['Last Heat ID'])

    print_dashboard_header()

    for idx, row in df.iterrows():
        # Gracefully handles empty/blank rows.
        if pd.isna(row['Last Heat ID']):
            continue

        heat_id = str(row['Last Heat ID'])
        
        # Mapped keys to match your updated ASCII-safe CSV headers.
        # Since pandas now imports these directly as float objects due to decimal=',', 
        # the float() cast below will run flawlessly.
        delta_si = float(row['Si-Jump'])
        delta_al = float(row['Al-Consumed'])

        # VTD Treatment is binary in the PoC dataset (1 or 0). 
        # The number '1' will be mapped to 25 minutes of high-intensity treatment (exceeding the 20 minute limit)
        # and the number '0' to 0 minutes to simulate temporal logic.
        vtd_time = 25.0 if int(row['VTD Treatment (Y/N)']) == 1 else 0.0

        # Calculations run through the predictive physics model.
        exo_delta = model.calculate_exothermic_delta(delta_si, delta_al)
        status = model.evaluate_operational_status(exo_delta, vtd_time)

        # Actions mapped to physical operational responses developed in report[cite: 91, 95, 96].
        if status == "RED":
            action = "🔴 REMOVE FROM CYCLE. Run dust removal blow-off & technical refractory verification."
        elif status == "YELLOW":
            action = "🟡 ALERT CREW: Execute focused post-cast visual refractory check."
        else:
            action = "🟢 Nominal cycle. Resume standard operations."
        
        print(f"{heat_id:<10} | {delta_si:<12.3f} | {delta_al:<12.3f} | {exo_delta:<10.3f} | {vtd_time:<8.1f} | {status:<10} | {action}")
    
    print("=" * 110)

if __name__ == "__main__":
    main()