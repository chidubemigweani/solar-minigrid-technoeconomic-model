import geopandas as gpd
import pandas as pd
import numpy as np

# Load data
settlements = gpd.read_file('/content/drive/MyDrive/blockgrid/done/settlements_complete.geojson')

def normalize_score(series, reverse=False, log_scale=False, clip_quantile=0.95):
    """
    Normalize series to 0-100 scale with options for log transformation
    and handling missing values.
    """
    # 1. Fill missing values with 0 to prevent crashes
    series = series.fillna(0)

    # 2. Log-transform skewed data (like population)
    # uses log1p (log(x+1)) to handle zeros safely
    if log_scale:
        series = np.log1p(series)

    min_val = series.min()
    max_val = series.quantile(clip_quantile)

    # Avoid division by zero if all values are the same
    if max_val == min_val:
        return pd.Series([50] * len(series))
    
    series_clipped = series.clip(upper=max_val)

    # 3. Calculate normalization
    normalized = ((series_clipped - min_val) / (max_val - min_val)) * 100

    if reverse:
        normalized = 100 - normalized

    return normalized

print("Calculating viability scores...")

# --- 1. MARKET SIZE SCORE (25%) ---
# UPDATED: Used log_scale=True for population to reduce outlier bias (The "Lagos" effect)
settlements['market_size_score'] = (
    normalize_score(settlements['pop'], log_scale=True) * 0.7 +
    normalize_score(settlements['pop_den'], log_scale=True) * 0.3
)

# --- 2. REVENUE POTENTIAL SCORE (25%) ---
# UPDATED: Log scale often helps nightlights too, as bright city centers are exponentially brighter
settlements['revenue_potential_score'] = (
    normalize_score(settlements['nightlight_intensity'], log_scale=True) * 0.6 +
    normalize_score(settlements['commercial_facilities_count']) * 0.4
)

# --- 3. COST EFFICIENCY SCORE (20%) ---
settlements['cost_efficiency_score'] = (
    normalize_score(settlements['solar_ghi']) * 0.7 +
    normalize_score(settlements['distance_to_grid_km'], reverse=False) * 0.3
)

# --- 4. ACCESSIBILITY SCORE (15%) ---
# UPDATED: Normalize EACH type first, then average.
# This prevents 50 small shops from making a town look better than one with a school/hospital.
settlements['accessibility_score'] = (
    normalize_score(settlements['schools_count']) * 0.4 +
    normalize_score(settlements['health_facilities_count']) * 0.4 +
    normalize_score(settlements['commercial_facilities_count']) * 0.2
)

# --- 5. STRATEGIC VALUE SCORE (15%) ---
# UPDATED: Removed 'population' to avoid double-counting.
# Focuses purely on the PRESENCE of key "Anchor" institutions.
anchor_score = (
    (settlements['health_facilities_count'] > 0).astype(int) * 60 + # Increaseds weight
    (settlements['schools_count'] > 0).astype(int) * 40             # Increased weight
)
# No need to normalize binary flags 0-100 if we sum them to 100, but keeping function for consistency
settlements['strategic_value_score'] = anchor_score # This is already 0-100 based on weights above

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

settlements['viability_tier'] = pd.cut(
    settlements['total_score'],
    bins=[0, 40, 70, 100],
    labels=['Low', 'Medium', 'High']
)

print(settlements.head())

# Save to specified Google Drive path for consistency
output_path = '/content/drive/MyDrive/blockgrid/done/settlements_scored.geojson'
settlements.to_file(output_path, driver='GeoJSON')

print(f"Scoring complete. Saved to {output_path}")
print(f"Top site: {settlements.iloc[0]['name']} - Score: {settlements.iloc[0]['total_score']:.1f}")