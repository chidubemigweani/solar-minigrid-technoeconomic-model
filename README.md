# Off-Grid Solar Mini-Grid Site Viability & Financial Modeling Pipeline

This repository contains a 7-stage geospatial and techno-economic modeling pipeline designed to identify, score, and evaluate the financial bankability of off-grid communities in Nigeria for solar mini-grid deployment. By combining satellite raster processing, vector spatial joins, multi-criteria decision analysis, and discounted cash flow modeling, the pipeline filters raw settlement data into an investment-ready portfolio of profitable mini-grid sites.

## Pipeline Architecture

The workflow executes sequentially across 7 modular Python scripts, passing intermediate GeoJSON checkpoints between stages:

1. **1_process_settlements.py**: Reprojects settlement points and population rasters to EPSG:32632, applies a 100m buffer to extract settlement populations, and filters for communities exceeding 500 residents.
2. **2_calculate_grid_distance.py**: Computes Euclidean distances from settlement centroids to transmission lines in EPSG:32632 using nearest-neighbor spatial joins and isolates off-grid sites beyond 2 km.
3. **3_count_infrastructure.py**: Deduplicates facility geometries and performs spatial joins within a 2,000m catchment buffer to count schools, healthcare centers, and commercial points per settlement.
4. **4_add_nightlights.py**: Queries VIIRS nighttime radiance at EPSG:4326 settlement centroids via nearest-neighbor interpolation and normalizes values to a 0–100 scale clipped at the 0.99 quantile.
5. **5_add_solar.py**: Samples Global Horizontal Irradiance rasters at settlement coordinates, standardizes energy units to kWh by dividing by 1,000 if the mean exceeds 100, and drops temporary index columns.
6. **6_calculate_scores.py**: Applies log-transformation and 0.95-quantile clipping to compute weighted composite viability scores, ranking sites and assigning Low, Medium, or High viability tiers.
7. **7_financial_projections.py**: Models system sizing, logistics-adjusted CAPEX, OPEX, after-tax WACC, 10-year NPV, payback periods, and Newton-Raphson IRR to filter bankable mini-grid sites.

## Multi-Criteria Viability Scoring

Stage 6 evaluates off-grid settlements across five weighted dimensions to balance demand volume, economic activity, and anchor load stability:

* **Normalization Logic**: Features scale from 0 to 100 with upper clipping at the 0.95 quantile and logarithmic transformation ($\ln(x+1)$) for skewed metrics to prevent urban outlier distortion.
* **Market Size (25%)**: Combines log-normalized total population (0.7 weight) and log-normalized population density (0.3 weight).
* **Revenue Potential (25%)**: Integrates log-normalized nighttime light intensity (0.6 weight) with commercial facility counts (0.4 weight).
* **Cost Efficiency (20%)**: Weights normalized solar irradiance (0.7 weight) alongside distance from the existing power grid (0.3 weight).
* **Accessibility (15%)**: Averages individually normalized counts of schools (0.4 weight), health facilities (0.4 weight), and commercial sites (0.2 weight).
* **Strategic Value (15%)**: Assigns binary anchor institution scores worth 60 points for healthcare presence and 40 points for school presence.
* **Viability Tiers**: Sites are ranked by composite score and segmented into Low (0 to 40), Medium (40 to 70), and High (70 to 100) tiers.

## Techno-Economic & Financial Model

Stage 7 translates physical settlement attributes into a capital budgeting model to test project bankability:

* **Demand Estimation**: Assumes a household size of 5, a 30% customer penetration rate, and a daily consumption of 1.0 kWh per connected customer over 365 days.
* **PV System Sizing**: Divides daily demand by solar yield (normalized against a 5.5 kWh/m²/day baseline across 4.0 peak sun hours) with a 1.30 oversizing margin.
* **CAPEX & OPEX**: Multiplies system kW by a $3,000 base cost and a remoteness factor ($1 + 0.001 \times \text{km}$), with annual OPEX set at 4% of CAPEX.
* **Revenue & Cash Flow**: Calculates annual revenue using a $0.60/kWh tariff and an 85% collection efficiency, subtracting annual OPEX to derive pre-tax cash flow.
* **Capital Structure (WACC)**: Blends 70% debt (22% interest) and 30% equity (25% return) with a 30% corporate tax shield to establish the discount hurdle rate:
$$\text{WACC} = (E \times r_e) + \left(D \times r_d \times (1 - t)\right)$$
* **Profitability Metrics**: Evaluates 10-year NPV, simple payback period, and Internal Rate of Return (solved via 100 Newton-Raphson iterations) to isolate NPV > 0 sites.

## Data Requirements & Outputs

* **Settlement & Population Inputs**: Uses GRID3 Nigeria settlement points (grid3_nga_settlementpt.shp) and WorldPop UN-adjusted population rasters (nga_ppp_2020_UNadj.tif).
* **Grid & Infrastructure Inputs**: Incorporates transmission network lines (power_lines.geojson) and point layers for schools, health, and commercial sites.
* **Satellite Environmental Inputs**: Extracts radiance from VIIRS nightlights (VNL_npp_2024_global.average_masked.dat.tif) and solar yield from GHI.tif.
* **Intermediate Spatial Checkpoints**: Outputs sequential GeoJSON files tracking base settlements, off-grid filtering, infrastructure counts, nightlights, and solar GHI.
* **Final Deliverables**: Generates ranked spatial layers (settlements_scored.geojson, settlements_financial_final.geojson) and tabular portfolios (pipeline.csv, pipeline_viable.csv).

## Setup & Execution

* **Python Environment**: Requires Python 3 with GeoPandas, Rasterio, Rasterstats, NumPy, and Pandas installed:

```bash
pip install geopandas rasterio rasterstats numpy pandas
```

* **Directory Configuration**: Update the base Google Drive file paths in each script to match your local or cloud storage directory structure before running.
* **Sequential Execution**: Run scripts in numerical order to build the full pipeline:

```bash
python 1_process_settlements.py
python 2_calculate_grid_distance.py
python 3_count_infrastructure.py
python 4_add_nightlights.py
python 5_add_solar.py
python 6_calculate_scores.py
python 7_financial_projections.py
```
