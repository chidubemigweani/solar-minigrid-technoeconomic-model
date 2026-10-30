import geopandas as gpd
import rasterio
from rasterstats import point_query
import numpy as np

# --- Load and Prepare Data ---
# 1. Load the GeoJSON file into a GeoDataFrame named settlements
settlements = gpd.read_file('/content/drive/MyDrive/blockgrid/done/settlements_with_infrastructure.geojson')
print("Settlement data loaded.")

# 2. Reproject the settlements GeoDataFrame to EPSG:4326
settlements_original_crs = settlements.crs
if settlements.crs != 'EPSG:4326':
    settlements = settlements.to_crs('EPSG:4326')
    print(f"Settlements GeoDataFrame reprojected from {settlements_original_crs} to EPSG:4326.")
else:
    print("Settlements GeoDataFrame already in EPSG:4326. No reprojection needed.")

# 3. Open the night-time light raster file using rasterio
nightlights_raster_path = '/content/drive/MyDrive/blockgrid/2_Night_Time_Lights/VNL_npp_2024_global.average_masked.dat.tif'
nightlights_raster = rasterio.open(nightlights_raster_path)
print(f"Night-time light raster file '{nightlights_raster_path}' opened.")

# Display the first few rows of the reprojected settlements GeoDataFrame and the raster CRS for verification
print("\nFirst 5 rows of reprojected settlements:")
print(settlements.head())
print("\nCRS of settlements GeoDataFrame:", settlements.crs)
print("\nCRS of nightlights raster:", nightlights_raster.crs)

# --- Extract Nightlight Intensity ---
# 1. Calculate the centroid for each geometry
settlements_centroids = settlements.geometry.centroid

# 2. Use rasterstats.point_query to query the night-time light intensity
print("Extracting night-time light intensity...")
light_values = point_query(
    settlements_centroids,
    nightlights_raster_path,
    interpolate='nearest'
)

# 3. Store these queried intensity values into a new column named 'nightlight_intensity'
settlements['nightlight_intensity'] = light_values

# Handle NoData values (which point_query returns as None or NaN) by filling with 0
settlements['nightlight_intensity'] = settlements['nightlight_intensity'].fillna(0)

# 4. Normalize to 0-100 scale using the 99th percentile
max_light = settlements['nightlight_intensity'].quantile(0.99)
settlements['nightlight_intensity'] = (settlements['nightlight_intensity'] / max_light * 100).clip(0, 100)

print("Night-time light intensity extracted, filled missing values, and normalized.")

# Display descriptive statistics and head of the updated GeoDataFrame for verification
print("\nDescriptive statistics for 'nightlight_intensity':")
print(settlements['nightlight_intensity'].describe())
print("\nFirst 5 rows with 'nightlight_intensity':")
print(settlements[['name', 'nightlight_intensity']].head())

# --- Save GeoDataFrame ---
output_path = '/content/drive/MyDrive/blockgrid/done/settlements_with_lights.geojson'

# Save the GeoDataFrame to a GeoJSON file
settlements.to_file(output_path, driver='GeoJSON')

print(f"Settlements GeoDataFrame with night-time light intensity saved to: {output_path}")