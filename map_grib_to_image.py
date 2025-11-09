#!/usr/bin/env python3
"""
Map GRIB2 Grid Points to Image Pixels

Now that we have the TRUE lat/lon for every GRIB2 grid point,
let's map them to image pixel coordinates and determine the
correct image bounds.

The approach:
1. Load GRIB2 lat/lon grids (919×1299)
2. These should map to the colored pixels in the image
3. Calculate what image bounds make this mapping correct

Usage:
    python3 map_grib_to_image.py
"""

import json
import numpy as np
from PIL import Image

def calculate_image_bounds_from_grib(lats, lons, image_path, label):
    """
    Calculate what the image bounds should be to align GRIB grid with image.

    Args:
        lats: 2D array of latitudes from GRIB2
        lons: 2D array of longitudes from GRIB2
        image_path: Path to reprojected image
        label: Label for output
    """
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]

    print(f"\nImage: {img_width} × {img_height} pixels")

    # Find data extent
    if img.mode == 'RGBA':
        a = img_array[:, :, 3]
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask = (a > 0) & has_color
    else:
        data_mask = np.any(img_array > 10, axis=2)

    rows_with_data = np.any(data_mask, axis=1)
    cols_with_data = np.any(data_mask, axis=0)

    row_indices = np.where(rows_with_data)[0]
    col_indices = np.where(cols_with_data)[0]

    data_top = row_indices[0]
    data_bottom = row_indices[-1]
    data_left = col_indices[0]
    data_right = col_indices[-1]

    data_height = data_bottom - data_top + 1
    data_width = data_right - data_left + 1

    print(f"\nData extent in image:")
    print(f"  Rows: {data_top} to {data_bottom} ({data_height} pixels)")
    print(f"  Cols: {data_left} to {data_right} ({data_width} pixels)")

    # GRIB2 grid dimensions
    grib_height, grib_width = lats.shape
    print(f"\nGRIB2 grid: {grib_height} × {grib_width}")

    # Convert lons to -180 to +180 range
    lons_180 = np.where(lons > 180, lons - 360, lons)

    # Geographic extent of GRIB2 grid
    lat_min = lats.min()
    lat_max = lats.max()
    lon_min = lons_180.min()
    lon_max = lons_180.max()

    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min

    print(f"\nGRIB2 geographic extent:")
    print(f"  Lat: {lat_min:.6f}° to {lat_max:.6f}° ({lat_range:.6f}°)")
    print(f"  Lon: {lon_min:.6f}° to {lon_max:.6f}° ({lon_range:.6f}°)")

    # Key calculation:
    # The GRIB2 grid (lat_min to lat_max) should map to the data pixels
    # (data_top to data_bottom) in the image.
    #
    # So we need to calculate what the IMAGE bounds should be.

    # Degrees per pixel based on GRIB range fitting into data pixels
    deg_per_pixel_lat = lat_range / data_height
    deg_per_pixel_lon = lon_range / data_width

    print(f"\nDegrees per pixel:")
    print(f"  Latitude:  {deg_per_pixel_lat:.6f}° per pixel")
    print(f"  Longitude: {deg_per_pixel_lon:.6f}° per pixel")

    # Calculate image bounds
    # If data_top should be at lat_max, then pixel 0 (image north) is:
    image_north = lat_max + (data_top * deg_per_pixel_lat)
    image_south = lat_max - ((data_bottom + 1) * deg_per_pixel_lat)

    # For longitude:
    image_west = lon_min - (data_left * deg_per_pixel_lon)
    image_east = lon_min + ((data_right + 1) * deg_per_pixel_lon)

    print(f"\n✨ CALCULATED Image Bounds:")
    print(f"  North: {image_north:.6f}°")
    print(f"  South: {image_south:.6f}°")
    print(f"  West:  {image_west:.6f}°")
    print(f"  East:  {image_east:.6f}°")

    # Verify: map GRIB corners to pixels
    print(f"\n🔍 Verification - GRIB extent should map to data pixels:")

    grib_north_pixel = (image_north - lat_max) / deg_per_pixel_lat
    grib_south_pixel = (image_north - lat_min) / deg_per_pixel_lat

    print(f"  GRIB north ({lat_max:.3f}°) -> pixel {grib_north_pixel:.1f} (data starts at {data_top})")
    print(f"  GRIB south ({lat_min:.3f}°) -> pixel {grib_south_pixel:.1f} (data ends at {data_bottom})")

    return {
        'image_bounds': [image_west, image_south, image_east, image_north],
        'data_pixels': {
            'top': int(data_top),
            'bottom': int(data_bottom),
            'left': int(data_left),
            'right': int(data_right),
            'width': int(data_width),
            'height': int(data_height)
        },
        'grib_extent': {
            'lat_min': float(lat_min),
            'lat_max': float(lat_max),
            'lon_min': float(lon_min),
            'lon_max': float(lon_max)
        },
        'deg_per_pixel': {
            'lat': float(deg_per_pixel_lat),
            'lon': float(deg_per_pixel_lon)
        }
    }


def main():
    print("="*70)
    print("Map GRIB2 Grid to Image Pixels")
    print("="*70)

    # Load GRIB2 lat/lon grids
    lats = np.load('hrrr_ak_latitudes.npy')
    lons = np.load('hrrr_ak_longitudes.npy')

    print(f"\nGRIB2 grids loaded: {lats.shape}")

    # Analyze western image
    western_result = calculate_image_bounds_from_grib(
        lats, lons,
        'images/alaska_hrrr_western.webp',
        'Western Image'
    )

    # Analyze eastern image
    eastern_result = calculate_image_bounds_from_grib(
        lats, lons,
        'images/alaska_hrrr_eastern.webp',
        'Eastern Image'
    )

    # Recommendation
    print(f"\n{'='*70}")
    print("FINAL RECOMMENDATION")
    print(f"{'='*70}")

    print(f"\n✅ Update test-data.json with these bounds:")
    print(f"\nWestern:")
    print(f"  {western_result['image_bounds']}")
    print(f"\nEastern:")
    print(f"  {eastern_result['image_bounds']}")

    # Save results
    results = {
        'western': western_result,
        'eastern': eastern_result
    }

    with open('grib_to_image_mapping.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📝 Results saved to: grib_to_image_mapping.json")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
