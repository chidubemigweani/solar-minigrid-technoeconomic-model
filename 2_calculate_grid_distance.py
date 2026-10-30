import geopandas as gpd

# --- Load and Prepare Data for Grid Distance ---
settlements = gpd.read_file('/content/drive/MyDrive/blockgrid/done/settlements_base.geojson')
print("Settlement data loaded.")
powerlines = gpd.read_file('/content/drive/MyDrive/blockgrid/4_Electricity_Grid/power_lines.geojson')
print("Power lines data loaded.")

# Reproject settlements GeoDataFrame to EPSG:32632 first for accurate centroid calculation
settlements_original_crs = settlements.crs
if settlements.crs != 'EPSG:32632':
    settlements = settlements.to_crs('EPSG:32632')
    print(f"Settlements GeoDataFrame reprojected from {settlements_original_crs} to EPSG:32632.")
else:
    print("Settlements GeoDataFrame already in EPSG:32632. No reprojection needed.")

# Convert settlement polygons to centroids
settlements['geometry'] = settlements.geometry.centroid
print("Settlement geometries converted to centroids.")

powerlines = powerlines.to_crs('EPSG:32632')
print("Power lines data reprojected to EPSG:32632.")

# --- Calculate Distance to Grid using sjoin_nearest ---
sj_nearest = gpd.sjoin_nearest(
    settlements,
    powerlines,
    how='left',
    distance_col='distance_meters'
)

sj_nearest['distance_to_grid_km'] = sj_nearest['distance_meters'] / 1000

# Merge the distance column back to the original settlements GeoDataFrame
# Using index for merging as 'id' column might not exist or be unique across all datasets
settlements_temp = settlements.reset_index()
sj_nearest_temp = sj_nearest.reset_index()

settlements = settlements_temp.merge(
    sj_nearest_temp[['index', 'distance_to_grid_km']],
    on='index',
    how='left'
).set_index('index')

print("Distance to nearest power line calculated and added to settlements.")
# Optional: Display for verification
# print("\nFirst 5 rows of settlements with 'distance_to_grid_km':")
# print(settlements[['name', 'geometry', 'distance_to_grid_km']].head())


# --- Filter settlements >2km from grid ---
settlements_offgrid = settlements[settlements['distance_to_grid_km'] > 2].copy()
print(f"Found {len(settlements_offgrid)} settlements more than 2km from the electricity grid.")


# --- Verify and Display Results ---
print("\nFirst 5 rows of settlements_offgrid GeoDataFrame:")
print(settlements_offgrid.head())

print("\nDescriptive statistics for 'distance_to_grid_km' in settlements_offgrid:")
print(settlements_offgrid['distance_to_grid_km'].describe())


# --- Save settlements_offgrid.geojson ---
output_path_offgrid = '/content/drive/MyDrive/blockgrid/done/settlements_offgrid.geojson'
settlements_offgrid.to_file(output_path_offgrid, driver='GeoJSON')
print(f"Filtered settlements GeoDataFrame saved to: {output_path_offgrid}")