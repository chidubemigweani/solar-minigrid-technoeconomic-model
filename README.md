# Solar Mini-Grid Technoeconomic Financial Model

## 📌 Project Overview
This project is a comprehensive technoeconomic analysis and financial model designed to assess the viability of **100kW Solar Hybrid Mini-Grids** for rural electrification in Nigeria. 

The tool bridges the gap between engineering design (load sizing) and investment banking (profitability), helping developers determine the exact subsidy required to make rural power "bankable" for private investors.

## 🚀 Key Features
* **Dynamic Load Profiling:** Algorithms to segment customers into "Household" (0.5 kWh/day) vs. "Productive Use" (2.0 kWh/day) to prevent system oversizing.
* **Financial KPI Engine:** automatically calculates **IRR, NPV, EBITDA**, and **Debt Service Coverage Ratio (DSCR)** over a 10-year lifecycle.
* **Scenario Manager:** Simulates "Commercial Debt" (18% interest) vs. "Blended Finance" (Grants + Soft Loans).
* **Sensitivity Analysis:** Stress-tests the model against Battery Degradation Costs ($250/kWh) and Tariff Fluctuations.

## 🛠️ Tech Stack
* **Python (Pandas, NumPy):** For cleaning load profile data and running Monte Carlo simulations on demand.
* **Advanced Excel:** For the 10-Year Cash Flow Waterfall and interactive dashboarding.
* **Sensitivity Analysis:** Standard deviation modeling for revenue risk.

## 📊 Key Results & Insights
* **The Subsidy Gap:** Analysis revealed that a purely commercial model results in bankruptcy (DSCR < 0.6).
* **The Solution:** A **40% CAPEX Grant** is required to achieve a **26% Return on Equity (ROE)**, making the project attractive to international infrastructure funds.
* **Optimization:** Customer segmentation reduced the required battery bank size by **15%**, saving ~$30,000 in upfront CAPEX.

## 📂 Project Structure
* `customer_scoring_algorithm.py` - A geospatial ranking engine that segments potential market sites using weighted economic indicators.
* `financial_projections_model.py` - A Python-based financial model that calculates 10-year Cash Flows, NPV, and CAPEX requirements for infrastructure investment.

## 📂 Code Structure

### 1. `customer_scoring_algorithm.py` (Site Selection Engine)
* **Purpose:** Ingests raw geospatial data to rank rural settlements based on economic viability.
* **Logic:** Implements a multi-criteria decision algorithm that weighs **Market Size (25%)**, **Economic Activity (25%)**, and **Grid Distance (20%)** to generate a "Viability Score" (0-100).
* **Key Feature:** Uses logarithmic normalization to handle population outliers, ensuring small but dense commercial clusters are not overlooked.

### 2. `financial_projections_model.py` (Technoeconomic Core)
* **Purpose:** Translates the scoring data into a 10-year bankability model for investment analysis.
* **Logic:** Simulates the full project lifecycle:
    * **Engineering:** Calculates required Solar PV & Battery capacity based on load profiles.
    * **CAPEX/OPEX:** Estimates hardware costs with logistics multipliers for remote sites.
    * **Financials:** Computes **NPV**, **Payback Period**, and **IRR** to filter for sites that meet the 12% Hurdle Rate.
* **Output:** Generates a "Viable Pipeline" CSV of sites ready for investment committee review.

---
*Note: Data and specific company metrics have not been included, the included have been anonymized for confidentiality.*
