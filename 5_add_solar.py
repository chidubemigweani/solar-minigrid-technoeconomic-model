import rasterio
import numpy as np
import geopandas as gpd # Ensure geopandas is imported for settlements GeoDataFrame

settlements = gpd.read_file('/content/drive/MyDrive/blockgrid/done/settlements_with_lights.geojson')
solar_raster_path = '/content/drive/MyDrive/blockgrid/3_Solar_Resource/GHI.tif'

print("--- Starting combined solar GHI processing ---")

# Reproject settlements to EPSG:4326 to match raster CRS
settlements_original_crs = settlements.crs
if settlements.crs != 'EPSG:4326':
    settlements = settlements.to_crs('EPSG:4326')
    print(f"Settlements GeoDataFrame reprojected from {settlements_original_crs} to EPSG:4326.")
else:
    print("Settlements GeoDataFrame already in EPSG:4326. No reprojection needed.")

# Ensure settlement geometries are points (centroids)
# The previous step in the notebook converted settlements to centroids, but a check is good practice.
if not all(settlements.geometry.type == 'Point'):
    settlements['geometry'] = settlements.geometry.centroid
    print("Settlement geometries converted to centroids.")
else:
    print("Settlement geometries are already points.")

# 1. Extract Solar GHI using rasterio.sample
print("Extracting solar GHI data using rasterio.sample...")
with rasterio.open(solar_raster_path) as src:
    raster_nodata = src.nodata
    print(f"Raster nodata value: {raster_nodata}")
    coords = [(x, y) for x, y in zip(settlements.geometry.x, settlements.geometry.y)]
    ghi_samples_generator = src.sample(coords, indexes=1)
    ghi_values = [s[0] for s in ghi_samples_generator]

if raster_nodata is not None:
    ghi_values = [val if val != raster_nodata else np.nan for val in ghi_values]
settlements['solar_ghi'] = ghi_values
print("Solar GHI extraction complete.")

# 2. Inspect and Normalize Solar GHI Data
print('\n--- Inspecting and Normalizing Solar GHI Data ---')
mean_ghi = settlements['solar_ghi'].mean()
print(f"Mean of 'solar_ghi': {mean_ghi:.3f}")

if mean_ghi > 100: # A conservative threshold to detect Wh values
    settlements['solar_ghi'] = settlements['solar_ghi'] / 1000
    print("Detected potential Wh units. Converted 'solar_ghi' to kWh by dividing by 1000.")
    mean_ghi = settlements['solar_ghi'].mean()
    print(f"New mean of 'solar_ghi' (kWh): {mean_ghi:.3f}")
else:
    print("'solar_ghi' values appear to be in kWh or an appropriate scale. No conversion needed.")

missing_ghi_count = settlements['solar_ghi'].isna().sum()
print(f"Number of missing (NaN) values in 'solar_ghi': {missing_ghi_count}")

columns_to_drop = ['index', 'id']
settlements = settlements.drop(columns=[col for col in columns_to_drop if col in settlements.columns])
print("Dropped 'index' and 'id' columns.")

print("Settlements GeoDataFrame after dropping 'index' and 'id' columns:")
print(settlements.head())

# 3. Save Updated GeoJSON
output_complete_path = '/content/drive/MyDrive/blockgrid/done/settlements_complete.geojson'
print('\n--- Saving updated GeoJSON ---')
settlements.to_file(output_complete_path, driver='GeoJSON')
print(f"Solar resource data added. Dataset complete with {len(settlements)} settlements. Saved to {output_complete_path}")

print("--- Combined solar GHI processing finished ---")