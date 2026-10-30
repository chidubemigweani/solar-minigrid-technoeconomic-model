import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np
from rasterio.io import MemoryFile
import warnings
import rasterio.mask

# --- Load and Reproject Settlement Data ---
# Load the shapefile into a GeoDataFrame
settlements_gdf = gpd.read_file('/content/drive/MyDrive/blockgrid/1_Population_and_Settlements/grid3_nga_settlementpt.shp')

# Reproject the GeoDataFrame to EPSG:32632
settlements_original_crs = settlements_gdf.crs
if settlements_gdf.crs != 'EPSG:32632':
    settlements_gdf = settlements_gdf.to_crs('EPSG:32632')
    print(f"Settlements GeoDataFrame reprojected from {settlements_original_crs} to EPSG:32632.")
else:
    print("Settlements GeoDataFrame already in EPSG:32632. No reprojection needed.")

# Display the first few rows and the CRS of the reprojected GeoDataFrame
print("First 5 rows of the reprojected GeoDataFrame:")
print(settlements_gdf.head())
print("\nCoordinate Reference System (CRS) of the reprojected GeoDataFrame:")
print(settlements_gdf.crs)

# --- Buffer and Convert Points to Polygons ---
settlements_gdf['geometry'] = settlements_gdf['geometry'].buffer(100)

# Display the first few rows of the updated GeoDataFrame and the geometry type
print("First 5 rows of the GeoDataFrame with buffered geometries:")
print(settlements_gdf.head())
print("\nGeometry type of the first entry after buffering:")
print(settlements_gdf.geometry.iloc[0].geom_type)

# --- Import rasterio and numpy - already imported at the top ---
print("rasterio and numpy imported.")

# --- Load and Reproject Population Raster - corrected version ---
population_raster_path = '/content/drive/MyDrive/blockgrid/1_Population_and_Settlements/nga_ppp_2020_UNadj.tif'
dst_crs = 'EPSG:32632'

with rasterio.open(population_raster_path) as src:
    # Calculate the transform and dimensions for the reprojected raster
    # Use calculate_default_transform to determine a suitable output extent.
    transform, width, height = rasterio.warp.calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds)

    # Create an empty array for the reprojected data
    reprojected_population_data = np.empty((height, width), dtype=src.profile['dtype'])

    # Perform the reprojection
    reproject(
        source=rasterio.band(src, 1), # Assuming population data is in the first band
        destination=reprojected_population_data,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        resampling=Resampling.average, # Use average resampling for population data
        dst_width=width, # Pass calculated width
        dst_height=height # Pass calculated height
    )

    # Update metadata for the reprojected raster
    reprojected_profile = src.profile.copy()
    reprojected_profile.update({
        'crs': dst_crs,
        'transform': transform,
        'width': width,
        'height': height,
        'nodata': src.nodata # Carry over nodata value
    })

# Store the reprojected data and its profile globally for later use
reprojected_population = {
    'data': reprojected_population_data,
    'profile': reprojected_profile
}

print(f"Reprojected population raster CRS: {reprojected_population['profile']['crs']}")
print(f"Reprojected population raster dimensions: {reprojected_population['profile']['width']}x{reprojected_population['profile']['height']}")

# --- Extract Population for Each Settlement - corrected version ---
# Create a MemoryFile from the reprojected population data and profile
# This allows rasterio.mask.mask to treat the in-memory array as a raster dataset.
with MemoryFile() as memfile:
    with memfile.open(**reprojected_population['profile']) as dataset:
        dataset.write(reprojected_population['data'], 1)

        # Initialize the 'pop' column in settlements_gdf
        settlements_gdf['pop'] = 0

        # Iterate through each settlement polygon and extract population
        for index, row in settlements_gdf.iterrows():
            geom = [row['geometry']]
            
            # Suppress warnings that might arise from masking empty geometries or other issues
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    # Extract population data for the current geometry
                    out_image, out_transform = rasterio.mask.mask(dataset, geom, crop=True, all_touched=False)

                    # Sum valid pixel values (excluding nodata) as integers
                    # Replace nodata values with NaN to exclude them from the sum
                    out_image[out_image == dataset.nodata] = np.nan
                    total_population = np.nansum(out_image).astype(int)
                    settlements_gdf.loc[index, 'pop'] = total_population
                except ValueError as e:
                    # Handle cases where geometry might not overlap with raster or other masking issues
                    if "Input shapes do not overlap raster" in str(e):
                        print(f"Warning: Geometry for settlement {row['set_name']} at index {index} does not overlap with raster.")
                    else:
                        print(f"Warning: Could not extract population for settlement {row['set_name']} at index {index}. Error: {e}")
                    settlements_gdf.loc[index, 'pop'] = 0 # Assign 0 population if extraction fails

# Display the first few rows with the new 'pop' column
print("First 5 rows of the GeoDataFrame with population data:")
print(settlements_gdf.head())

# --- Calculate Area and Population Density ---
# Calculate the area of each buffered settlement polygon in square meters
settlements_gdf['area_m2'] = settlements_gdf.geometry.area

# Calculate population density in persons/m²
# Handle potential division by zero if area_m2 is 0
settlements_gdf['pop_den_m2'] = settlements_gdf.apply(lambda row: row['pop'] / row['area_m2'] if row['area_m2'] > 0 else 0, axis=1)

# Convert population density from persons/m² to persons/km²
settlements_gdf['pop_den_km2'] = settlements_gdf['pop_den_m2'] * 1_000_000

# Display the first few rows with the new columns
print("First 5 rows of the GeoDataFrame with area and population density:")
print(settlements_gdf.head())

# --- Filter, Rename, and Select Columns - corrected version ---
# 1. Filter the GeoDataFrame to include only settlements with a population greater than 500
filtered_settlements_gdf = settlements_gdf[settlements_gdf['pop'] > 500].copy()

# 2. Calculate latitude and longitude
# Reproject to EPSG:4326 to get proper latitude and longitude from centroids
filtered_settlements_gdf_wgs84 = filtered_settlements_gdf.to_crs(epsg=4326)
# Suppress UserWarning about `crs` in `GeoSeries.x` and `GeoSeries.y`
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    filtered_settlements_gdf['longitude'] = filtered_settlements_gdf_wgs84.geometry.centroid.x
    filtered_settlements_gdf['latitude'] = filtered_settlements_gdf_wgs84.geometry.centroid.y

# 3. Rename the specified columns
filtered_settlements_gdf = filtered_settlements_gdf.rename(columns={
    'set_name': 'name',
    'statename': 'state',
    'lganame': 'lga',
    'pop_den_km2': 'pop_den'
})

# 4. Select the final columns, including 'geometry' to keep it as a GeoDataFrame
final_columns = ['name', 'state', 'lga', 'latitude', 'longitude', 'pop', 'pop_den', 'geometry']
final_settlements_gdf = filtered_settlements_gdf[final_columns]

# Display the first few rows of the final GeoDataFrame
print("First 5 rows of the final GeoDataFrame:")
print(final_settlements_gdf.head())

# Display a summary of the analysis as requested in the main task
print(f"\nTotal settlements after filtering (pop > 500): {len(final_settlements_gdf)}")
print(f"Average population: {final_settlements_gdf['pop'].mean():.2f}")
print(f"Average population density (persons/km²): {final_settlements_gdf['pop_den'].mean():.2f}")

# --- Save GeoDataFrame to GeoJSON ---
output_filepath = '/content/drive/MyDrive/blockgrid/done/settlements_base.geojson'
final_settlements_gdf.to_file(output_filepath, driver='GeoJSON')
print(f"GeoDataFrame saved to {output_filepath}")