import geopandas as gpd
import pandas as pd
import numpy as np
import os

# --- 1. GLOBAL ASSUMPTIONS (The "Control Panel") ---
# Market Assumptions
CUSTOMER_PENETRATION = 0.30     # We assume 30% of the village will sign up
AVG_HOUSEHOLD_SIZE = 5          # People per home
DAILY_KWH_PER_CUSTOMER = 1.0    # Productive use target (Commercial + Residential mix)

# Engineering Assumptions
SYSTEM_OVERSIZING = 1.45        # 1.45 DC/AC Ratio to account for battery charging & heat loss
BASELINE_GHI = 5.5              # Reference Solar Irradiance (kWh/m2/day)

# Financial Assumptions (USD)
CAPEX_PER_KW = 3000.0           # Hardware + Installation cost per kW
OPEX_PERCENT = 0.04             # Maintenance is 4% of CAPEX annually
TARIFF_PER_KWH = 0.60           # Cost of electricity to consumer
COLLECTION_RATE = 0.85          # 85% Collection Efficiency (15% Technical/Commercial Loss)
DISCOUNT_RATE = 0.12            # 12% WACC (Weighted Average Cost of Capital)
PROJECT_LIFETIME = 10           # Analysis period in Years

def run_financial_projections(input_path, output_dir):
    """
    Performs technoeconomic modeling on scored settlements.
    Calculates CAPEX, OPEX, Cash Flows, NPV, and ROI to filter for bankable sites.
    """
    print("--- Starting Financial Projection Engine ---")
    
    # Load Data
    try:
        settlements = gpd.read_file(input_path)
    except Exception as e:
        print(f"Error loading input file: {e}")
        return

    print(f"Loaded {len(settlements)} sites. Calculating projections...")

    # --- PHASE 1: ENGINEERING SIZING ---
    
    # 1. Estimate Total Load
    # Logic: Population -> Households -> Customers -> Total Daily kWh
    households = settlements['pop'] / AVG_HOUSEHOLD_SIZE
    settlements['estimated_customers'] = (households * CUSTOMER_PENETRATION).astype(int)
    settlements['estimated_demand_kwh_day'] = settlements['estimated_customers'] * DAILY_KWH_PER_CUSTOMER

    # 2. System Sizing (Solar PV Capacity)
    # Logic: Adjust local GHI against baseline. If local sun is stronger, we need fewer panels.
    # Formula: (Demand / Peak Sun Hours) * Oversizing_Factor
    ghi_factor = settlements['solar_ghi'].fillna(BASELINE_GHI).replace(0, BASELINE_GHI) / BASELINE_GHI
    settlements['system_size_kw'] = (settlements['estimated_demand_kwh_day'] / (ghi_factor * 4)) * SYSTEM_OVERSIZING

    # --- PHASE 2: CAPEX & OPEX MODELING ---

    # 3. CAPEX Calculation with Logistics Penalty
    # Logic: Projects further from the grid are harder to reach. 
    # Penalty: Add 10% cost for every 100km distance from the main grid.
    logistics_mult = 1 + (settlements['distance_to_grid_km'] / 100) * 0.1
    settlements['capex_estimate_usd'] = settlements['system_size_kw'] * CAPEX_PER_KW * logistics_mult

    # 4. Operating Expenses & Revenue
    settlements['opex_annual_usd'] = settlements['capex_estimate_usd'] * OPEX_PERCENT
    
    # Revenue = Annual Energy Sold * Tariff * Collection Rate
    annual_energy_sales = settlements['estimated_demand_kwh_day'] * 365
    settlements['revenue_annual_usd'] = annual_energy_sales * TARIFF_PER_KWH * COLLECTION_RATE

    # --- PHASE 3: FINANCIAL METRICS (The "Bankability" Check) ---

    # 5. Cash Flow Analysis
    annual_cashflow = settlements['revenue_annual_usd'] - settlements['opex_annual_usd']
    settlements['annual_cashflow_usd'] = annual_cashflow

    # Metric A: Payback Period (Years)
    # Logic: How many years to earn back the initial CAPEX?
    # Handle negative cashflows (projects that lose money) by assigning a Sentinel Value (999)
    settlements['payback_years'] = np.where(
        annual_cashflow > 0,
        settlements['capex_estimate_usd'] / annual_cashflow,
        999 
    )

    # Metric B: Net Present Value (NPV)
    # Logic: Determine the value of future cash flows in today's dollars using the Annuity Formula.
    # Formula: NPV = -Investment + (Annual_Cashflow * Annuity_Factor)
    annuity_factor = (1 - (1 + DISCOUNT_RATE) ** (-PROJECT_LIFETIME)) / DISCOUNT_RATE
    settlements['npv_10yr_usd'] = -settlements['capex_estimate_usd'] + (annual_cashflow * annuity_factor)

    # Metric C: Simple Yield (First Year ROI)
    with np.errstate(divide='ignore', invalid='ignore'):
        settlements['simple_yield_percent'] = (annual_cashflow / settlements['capex_estimate_usd']) * 100
        # Clean up infinite values for sites with 0 CAPEX (edge cases)
        settlements['simple_yield_percent'] = settlements['simple_yield_percent'].replace([np.inf, -np.inf], 0).fillna(0)

    # --- PHASE 4: FILTERING & EXPORT ---

    # Definition of "Viable": Positive NPV AND Payback < 7 Years
    viable_sites = settlements[
        (settlements['npv_10yr_usd'] > 0) &
        (settlements['payback_years'] < 7)
    ].copy()

    # Formatting for clean output
    cols_to_round = ['system_size_kw', 'capex_estimate_usd', 'revenue_annual_usd', 'npv_10yr_usd', 'payback_years', 'simple_yield_percent']
    settlements[cols_to_round] = settlements[cols_to_round].round(1)

    # Console Summary
    print("-" * 40)
    print(f"Total Sites Processed: {len(settlements)}")
    print(f"Bankable Opportunities: {len(viable_sites)} ({(len(viable_sites)/len(settlements)):.1%})")
    print(f"Total CAPEX Required:   ${viable_sites['capex_estimate_usd'].sum() / 1e6:.2f} Million")
    print("-" * 40)

    print("\n=== TOP 5 SITES (By NPV) ===")
    display_cols = ['name', 'state', 'pop', 'capex_estimate_usd', 'payback_years', 'npv_10yr_usd']
    # Use .get() to handle cases where 'name' or 'state' might be missing in test data
    available_cols = [c for c in display_cols if c in viable_sites.columns]
    
    print(viable_sites[available_cols]
          .sort_values('npv_10yr_usd', ascending=False).head(5))

    # Save Results
    os.makedirs(output_dir, exist_ok=True)
    
    # Save Full Dataset (GeoJSON)
    settlements.to_file(os.path.join(output_dir, 'financial_projections_full.geojson'), driver='GeoJSON')
    
    # Save Viable Pipeline (CSV) for Excel reporting
    viable_sites.to_csv(os.path.join(output_dir, 'viable_project_pipeline.csv'), index=False)
    
    print(f"\nSuccess! Reports saved to: {output_dir}")

if __name__ == "__main__":
    # Define paths
    INPUT_FILE = './output/scored_settlements.geojson'  # Output from the first script
    OUTPUT_DIR = './output/financial_reports/'
    
    run_financial_projections(INPUT_FILE, OUTPUT_DIR)