import geopandas as gpd
import pandas as pd
import numpy as np
import os

# --- 1. CONFIGURATION (The "Recommendation" Case) ---

# Paths
INPUT_PATH = '/content/drive/MyDrive/blockgrid/done/settlements_scored.geojson'
OUTPUT_PATH_GEOJSON = '/content/drive/MyDrive/blockgrid/done/settlements_financial_final.geojson'
OUTPUT_PATH_ALL_CSV = '/content/drive/MyDrive/blockgrid/done/pipeline.csv'
OUTPUT_PATH_VIABLE_CSV = '/content/drive/MyDrive/blockgrid/done/pipeline_viable.csv'

# Market Assumptions
CUSTOMER_PENETRATION = 0.30     # 30% of population
AVG_HOUSEHOLD_SIZE = 5
DAILY_KWH_PER_CUSTOMER = 1.0

# Engineering Assumptions
SYSTEM_OVERSIZING = 1.30        # Standard safety margin
BASELINE_GHI = 5.5              # High-yield solar resource zone

# Financial Assumptions
CAPEX_PER_KW = 3000.0           # Global Benchmark for efficient developers
OPEX_PERCENT = 0.04             # 4.0% covers staff, software, and minor replacements
TARIFF_PER_KWH = 0.60           # Solvency rate to cover OPEX and debt
COLLECTION_RATE = 0.85          # Requirement for business viability
PROJECT_LIFETIME = 10

# Capital Structure (WACC Inputs)
DEBT_RATIO = 0.70               # 70% Bank Loan
EQUITY_RATIO = 0.30             # 30% Investor Equity
COST_OF_DEBT = 0.22             # 22% Interest Rate
COST_OF_EQUITY = 0.25           # 25% Investor Expectation
TAX_RATE = 0.30                 # 30% Corporate Tax

# --- 2. HELPER FUNCTIONS ---

def calculate_wacc(debt_ratio, cost_of_debt, cost_of_equity, tax_rate):
    """
    Calculates WACC with Tax Shield.
    Formula: (%Equity * Cost_Equity) + (%Debt * Cost_Debt * (1 - Tax_Rate))
    """
    cost_of_debt_after_tax = cost_of_debt * (1 - tax_rate)
    wacc = (EQUITY_RATIO * cost_of_equity) + (debt_ratio * cost_of_debt_after_tax)
    return wacc

def calculate_irr_manual(cashflows):
    """
    Calculates IRR manually using Newton-Raphson approximation.
    """
    rate = 0.1
    for _ in range(100):
        npv = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cashflows))
        derivative = sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cashflows))

        if abs(derivative) < 1e-5: return rate
        new_rate = rate - (npv / derivative)

        if abs(new_rate - rate) < 1e-5: return new_rate
        rate = new_rate
    return rate

# --- 3. MAIN EXECUTION ---

print("--- Starting Single Scenario Financial Modeling ---")

# 1. Calculate WACC
wacc = calculate_wacc(DEBT_RATIO, COST_OF_DEBT, COST_OF_EQUITY, TAX_RATE)
print(f"Calculated WACC (Hurdle Rate): {wacc*100:.2f}%")

# 2. Load Data
settlements = gpd.read_file(INPUT_PATH)
print(f"Loaded {len(settlements)} settlements.")

# 3. Demand & Sizing Calculations
# Estimate Customers
settlements['estimated_customers'] = (settlements['pop'] / AVG_HOUSEHOLD_SIZE * CUSTOMER_PENETRATION).astype(int)

# Estimate Demand (kWh/day)
settlements['estimated_demand_kwh_day'] = settlements['estimated_customers'] * DAILY_KWH_PER_CUSTOMER

# Normalize Solar GHI
# Sites with GHI < Baseline need larger systems to produce same energy
ghi_factor = settlements['solar_ghi'].fillna(BASELINE_GHI).replace(0, BASELINE_GHI) / BASELINE_GHI

# Calculate System Size (kW)
# Formula: Demand / (Yield_Factor * Peak_Sun_Hours) * Safety_Margin
settlements['system_size_kw'] = (settlements['estimated_demand_kwh_day'] / (ghi_factor * 4.0)) * SYSTEM_OVERSIZING

# 4. CAPEX & OPEX Calculations
# Logistics adjustment: Costs increase by 0.1% for every km from grid (proxy for remoteness)
logistics_mult = 1 + (settlements['distance_to_grid_km'] / 100) * 0.1

# CAPEX
settlements['capex_estimate_usd'] = settlements['system_size_kw'] * CAPEX_PER_KW * logistics_mult

# OPEX
settlements['opex_annual_usd'] = settlements['capex_estimate_usd'] * OPEX_PERCENT

# 5. Revenue & Cash Flow
# Annual Sales
annual_energy_sales = settlements['estimated_demand_kwh_day'] * 365
settlements['revenue_annual_usd'] = annual_energy_sales * TARIFF_PER_KWH * COLLECTION_RATE

# Free Cash Flow (Pre-Tax for simplicity)
settlements['annual_cashflow_usd'] = settlements['revenue_annual_usd'] - settlements['opex_annual_usd']

# 6. NPV & Payback Calculations
# Annuity factor for steady cash flows over project lifetime
annuity_factor = (1 - (1 + wacc) ** (-PROJECT_LIFETIME)) / wacc
settlements['npv_10yr_usd'] = -settlements['capex_estimate_usd'] + (settlements['annual_cashflow_usd'] * annuity_factor)

# Payback Period
settlements['payback_years'] = np.where(
    settlements['annual_cashflow_usd'] > 0,
    settlements['capex_estimate_usd'] / settlements['annual_cashflow_usd'],
    999
)

# 7. IRR Calculation
print("Calculating IRR for viable sites...")
settlements['irr_percent'] = 0.0
viable_indices = settlements[settlements['annual_cashflow_usd'] > 0].index

irr_results = []
for idx in viable_indices:
    row = settlements.loc[idx]
    # Cashflow array: Year 0 (negative CAPEX), Years 1-10 (positive Cashflow)
    cf = [-row['capex_estimate_usd']] + [row['annual_cashflow_usd']] * PROJECT_LIFETIME
    irr = calculate_irr_manual(cf)
    irr_results.append(irr * 100)

settlements.loc[viable_indices, 'irr_percent'] = irr_results

# 8. Filtering & Export
# Filter for positive NPV
viable_projects = settlements[settlements['npv_10yr_usd'] > 0].copy()

# Formatting for readability
cols_to_round = ['system_size_kw', 'capex_estimate_usd', 'revenue_annual_usd', 'npv_10yr_usd', 'irr_percent']
settlements[cols_to_round] = settlements[cols_to_round].round(1)
viable_projects[cols_to_round] = viable_projects[cols_to_round].round(1)

print("\n=== FINANCIAL RESULTS ===")
print(f"Total Sites Analyzed: {len(settlements)}")
print(f"Bankable Sites (NPV > 0): {len(viable_projects)}")
if not viable_projects.empty:
    print(f"Average IRR (Viable Sites): {viable_projects['irr_percent'].mean():.2f}%")
    print(f"Total CAPEX Required: ${viable_projects['capex_estimate_usd'].sum()/1e6:.2f} Million")
else:
    print("No sites met the profitability criteria.")

# --- SAVE FILES ---
print(f"\nSaving output files...")

# 1. GeoJSON (All Sites)
settlements.to_file(OUTPUT_PATH_GEOJSON, driver='GeoJSON')
print(f"Saved GeoJSON: {OUTPUT_PATH_GEOJSON}")

# 2. CSV (All Sites)
settlements.to_csv(OUTPUT_PATH_ALL_CSV, index=False)
print(f"Saved CSV (All): {OUTPUT_PATH_ALL_CSV}")

# 3. CSV (Viable Sites Only)
viable_projects.to_csv(OUTPUT_PATH_VIABLE_CSV, index=False)
print(f"Saved CSV (Viable): {OUTPUT_PATH_VIABLE_CSV}")

print("\nProcessing complete.")