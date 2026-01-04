import geopandas as gpd
import pandas as pd
import numpy as np
import os

def normalize_score(series, reverse=False, log_scale=False):
    """
    Normalizes a pandas Series to a 0-100 scale using Min-Max scaling.
    
    Args:
        series (pd.Series): The numerical data to normalize.
        reverse (bool): If True, lower values get higher scores (e.g., for distance metrics).
        log_scale (bool): If True, applies log transformation (np.log1p) to handle skewed data.
        
    Returns:
        pd.Series: Normalized scores from 0 to 100.
    """
    # 1. Fill missing values with 0 to prevent calculation errors
    series = series.fillna(0)

    # 2. Log-transform skewed data (e.g., Population counts often follow power laws)
    if log_scale:
        series = np.log1p(series)

    min_val = series.min()
    max_val = series.max()

    # Avoid division by zero if all values are identical
    if max_val == min_val:
        return pd.Series([50] * len(series), index=series.index)

    # 3. Calculate normalization
    normalized = ((series - min_val) / (max_val - min_val)) * 100

    if reverse:
        normalized = 100 - normalized

    return normalized

def calculate_viability_scores(input_path, output_path):
    """
    Loads settlement data, calculates weighted viability scores for mini-grid suitability,
    and saves the ranked results to a new GeoJSON file.
    """
    print(f"Loading data from {input_path}...")
    
    try:
        settlements = gpd.read_file(input_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print("Calculating viability scores...")

    # --- 1. MARKET SIZE SCORE (25%) ---
    # Metric: Measures the raw potential customer base.
    # Note: Log scale used to reduce the bias of massive outliers (e.g., large towns vs villages).
    settlements['market_size_score'] = (
        normalize_score(settlements['pop'], log_scale=True) * 0.7 +
        normalize_score(settlements['pop_den'], log_scale=True) * 0.3
    )

    # --- 2. REVENUE POTENTIAL SCORE (25%) ---
    # Metric: Proxies for economic activity (Nightlights and Commercial clusters).
    settlements['revenue_potential_score'] = (
        normalize_score(settlements['nightlight_intensity'], log_scale=True) * 0.6 +
        normalize_score(settlements['commercial_facilities_count']) * 0.4
    )

    # --- 3. COST EFFICIENCY SCORE (20%) ---
    # Metric: Technical feasibility. Higher Solar GHI (Irradiance) is better.
    # Distance to Grid: Typically, mini-grids target off-grid areas, so further is often 'better' 
    # to avoid grid encroachment risk.
    settlements['cost_efficiency_score'] = (
        normalize_score(settlements['solar_ghi']) * 0.7 +
        normalize_score(settlements['distance_to_grid_km'], reverse=False) * 0.3
    )

    # --- 4. ACCESSIBILITY SCORE (15%) ---
    # Metric: Infrastructure presence.
    # Normalized individually to prevent one metric (e.g., small shops) from skewing the total.
    settlements['accessibility_score'] = (
        normalize_score(settlements['schools_count']) * 0.4 +
        normalize_score(settlements['health_facilities_count']) * 0.4 +
        normalize_score(settlements['commercial_facilities_count']) * 0.2
    )

    # --- 5. STRATEGIC VALUE SCORE (15%) ---
    # Metric: "Anchor Customer" presence.
    # Focuses purely on the binary PRESENCE of key institutions (School/Hospital),
    # as these often serve as reliable payers (Anchor Load).
    anchor_score = (
        (settlements['health_facilities_count'] > 0).astype(int) * 60 + 
        (settlements['schools_count'] > 0).astype(int) * 40             
    )
    settlements['strategic_value_score'] = anchor_score 

    # --- TOTAL WEIGHTED SCORE ---
    weights = {
        'market_size_score': 0.25,
        'revenue_potential_score': 0.25,
        'cost_efficiency_score': 0.20,
        'accessibility_score': 0.15,
        'strategic_value_score': 0.15
    }

    settlements['total_score'] = sum(
        settlements[score] * weight
        for score, weight in weights.items()
    )

    # --- RANK & TIER ---
    settlements = settlements.sort_values('total_score', ascending=False)
    settlements['rank'] = range(1, len(settlements) + 1)

    # Categorize into simple tiers for business decision making
    settlements['viability_tier'] = pd.cut(
        settlements['total_score'],
        bins=[0, 40, 70, 100],
        labels=['Low', 'Medium', 'High']
    )

    # Save Results
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    settlements.to_file(output_path, driver='GeoJSON')
    print(f"Scoring complete. Results saved to {output_path}")
    
    # Validation Print (Sanity Check)
    if not settlements.empty:
        top_site = settlements.iloc[0]
        # Use .get() to avoid errors if 'name' column is missing in test data
        print(f"Top Ranked Site: {top_site.get('name', 'Unknown Location')} - Score: {top_site['total_score']:.1f}")

if __name__ == "__main__":
    # Define paths (Relative paths for portability)
    INPUT_FILE = './data/raw_settlements.geojson'
    OUTPUT_FILE = './output/scored_settlements.geojson'
    
    calculate_viability_scores(INPUT_FILE, OUTPUT_FILE)