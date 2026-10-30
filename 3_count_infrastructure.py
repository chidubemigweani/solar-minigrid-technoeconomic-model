import geopandas as gpd

print("Starting infrastructure counting and saving process...")

# --- 1. Load and Reproject Data ---
# Load the 'settlements_offgrid.geojson' file
settlements = gpd.read_file('/content/drive/MyDrive/blockgrid/done/settlements_offgrid.geojson')

# Add a unique identifier column named 'id' to the settlements GeoDataFrame
if 'id' not in settlements.columns:
    settlements['id'] = range(len(settlements))
    print("Added 'id' column to settlements GeoDataFrame.")
else:
    print("'id' column already exists in settlements GeoDataFrame.")

# Load infrastructure data
schools = gpd.read_file('/content/drive/MyDrive/blockgrid/5_Infrastructure/schools.geojson')
health = gpd.read_file('/content/drive/MyDrive/blockgrid/5_Infrastructure/health.geojson')
commercial = gpd.read_file('/content/drive/MyDrive/blockgrid/5_Infrastructure/commercial.geojson')

print("All GeoJSON files loaded. Reprojecting to 'EPSG:32632'...")

# Reproject all GeoDataFrames to 'EPSG:32632'
settlements_original_crs = settlements.crs
if settlements.crs != 'EPSG:32632':
    settlements = settlements.to_crs('EPSG:32632')
    print(f"Settlements GeoDataFrame reprojected from {settlements_original_crs} to EPSG:32632.")
else:
    print("Settlements GeoDataFrame already in EPSG:32632. No reprojection needed.")
schools = schools.to_crs('EPSG:32632')
health = health.to_crs('EPSG:32632')
commercial = commercial.to_crs('EPSG:32632')

print("Reprojection complete.")

# --- 2. Prepare Infrastructure Data (Drop Duplicates) ---
print("Checking for and dropping duplicate geometries in infrastructure GeoDataFrames...")
schools = schools.drop_duplicates(subset=['geometry'])
health = health.drop_duplicates(subset=['geometry'])
commercial = commercial.drop_duplicates(subset=['geometry'])
print("Duplicate geometry removal complete.")

# --- 3. Create Settlement Buffers ---
print("Generating 2km buffers around each settlement point...")
buffer_distance_m = 2000
settlement_buffers = settlements.copy()
settlement_buffers['geometry'] = settlements.geometry.buffer(buffer_distance_m)
print("Settlement buffers created.")

# --- 4. Spatially Join and Count Infrastructure ---
print("Performing spatial joins and counting infrastructure within 2km buffers...")

# Spatial join for schools
schools_in_buffers = gpd.sjoin(settlement_buffers, schools, how='inner', predicate='intersects')
schools_count_df = schools_in_buffers.groupby('id').size().reset_index(name='schools_count')

# Spatial join for health facilities
health_in_buffers = gpd.sjoin(settlement_buffers, health, how='inner', predicate='intersects')
health_count_df = health_in_buffers.groupby('id').size().reset_index(name='health_facilities_count')

# Spatial join for commercial facilities
commercial_in_buffers = gpd.sjoin(settlement_buffers, commercial, how='inner', predicate='intersects')
commercial_count_df = commercial_in_buffers.groupby('id').size().reset_index(name='commercial_facilities_count')

print("Spatial joins and counting complete.")

# --- 5. Merge Counts to Settlements ---
print("Merging infrastructure counts back into the settlements GeoDataFrame...")
settlements = settlements.merge(schools_count_df, on='id', how='left')
settlements = settlements.merge(health_count_df, on='id', how='left')
settlements = settlements.merge(commercial_count_df, on='id', how='left')

# Fill any NaN values with 0 and convert to integer
settlements['schools_count'] = settlements['schools_count'].fillna(0).astype(int)
settlements['health_facilities_count'] = settlements['health_facilities_count'].fillna(0).astype(int)
settlements['commercial_facilities_count'] = settlements['commercial_facilities_count'].fillna(0).astype(int)

print("Merge complete.")

# --- 6. Display Final Results ---
print("\nFirst 5 rows of the final settlements GeoDataFrame with infrastructure counts:")
print(settlements.head())
print("\nColumn names and data types of the final 'settlements' GeoDataFrame:")
print(settlements.info())

# --- 7. Save Final Results ---
output_path = '/content/drive/MyDrive/blockgrid/done/settlements_with_infrastructure.geojson'
print(f"\nSaving settlements GeoDataFrame with infrastructure counts to {output_path}...")
settlements.to_file(output_path, driver='GeoJSON')
print("Save complete.")