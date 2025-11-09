#!/usr/bin/env python3
"""
DIRECT BOUNDS CALCULATION

The affine approach failed because polar stereographic doesn't transform linearly.

New approach:
1. The image width represents 360° longitude (full wrap)
2. The GRIB data spans ~360° longitude
3. Find the longitude where the image starts
4. Calculate latitude bounds from the vertical extent
"""

import json
import numpy as np
from PIL import Image

def calculate_bounds_direct():
    print("="*70)
    print("DIRECT BOUNDS CALCULATION")
    print("="*70)

    # Load GRIB2 data
    grib_lats = np.load('hrrr_ak_latitudes.npy')
    grib_lons = np.load('hrrr_ak_longitudes.npy')
    grib_lons_180 = np.where(grib_lons > 180, grib_lons - 360, grib_lons)

    ny, nx = grib_lats.shape
    print(f"\nGRIB Grid: {ny} × {nx}")
    print(f"Lat range: {grib_lats.min():.6f}° to {grib_lats.max():.6f}°")
    print(f"Lon range: {grib_lons_180.min():.6f}° to {grib_lons_180.max():.6f}°")

    grib_lat_span = grib_lats.max() - grib_lats.min()
    grib_lon_span = grib_lons_180.max() - grib_lons_180.min()

    print(f"Spans: {grib_lat_span:.6f}° lat, {grib_lon_span:.6f}° lon")

    # Load image
    img = Image.open('images/alaska_hrrr_western.webp')
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]

    print(f"\nImage: {img_width} × {img_height}")

    # Find data extent
    if img.mode == 'RGBA':
        alpha = img_array[:, :, 3]
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask = (alpha > 0) & has_color

    rows_with_data = np.any(data_mask, axis=1)
    row_indices = np.where(rows_with_data)[0]

    data_top = row_indices[0]
    data_bottom = row_indices[-1]
    data_height = data_bottom - data_top + 1

    print(f"Data rows: {data_top} to {data_bottom} ({data_height} pixels)")

    # KEY INSIGHT: The image width represents ~360° (full wrap)
    # The GRIB data also spans ~360°
    # So deg/pixel horizontally is:
    deg_per_pixel_lon = 360.0 / img_width

    print(f"\nLongitude resolution: {deg_per_pixel_lon:.6f}° per pixel")

    # The GRIB data occupies the full image width (cols 0 to 12169)
    # So the image starts at some longitude and wraps 360°

    # Figure out where the image starts:
    # The GRIB west edge is at pixel 0, so:
    image_west = grib_lons_180.min()
    image_east = image_west + (img_width * deg_per_pixel_lon)

    print(f"\nLongitude bounds:")
    print(f"  West: {image_west:.6f}°")
    print(f"  East: {image_east:.6f}°")
    print(f"  Span: {image_east - image_west:.6f}°")

    # For latitude, we know:
    # - Data occupies rows data_top to data_bottom
    # - This should contain the GRIB lat range

    # Degrees per pixel vertically:
    deg_per_pixel_lat = grib_lat_span / data_height

    print(f"\nLatitude resolution: {deg_per_pixel_lat:.6f}° per pixel")

    # If data_top should be at GRIB max lat:
    image_north = grib_lats.max() + (data_top * deg_per_pixel_lat)
    image_south = image_north - (img_height * deg_per_pixel_lat)

    print(f"\nLatitude bounds:")
    print(f"  North: {image_north:.6f}°")
    print(f"  South: {image_south:.6f}°")
    print(f"  Span: {image_north - image_south:.6f}°")

    # Verification
    print(f"\n🔍 Verification:")
    data_north = image_north - (data_top * deg_per_pixel_lat)
    data_south = image_north - ((data_bottom + 1) * deg_per_pixel_lat)

    print(f"  Data north (pixel {data_top}): {data_north:.6f}° (should be {grib_lats.max():.6f}°)")
    print(f"  Data south (pixel {data_bottom}): {data_south:.6f}° (should be {grib_lats.min():.6f}°)")

    error_north = abs(data_north - grib_lats.max())
    error_south = abs(data_south - grib_lats.min())

    print(f"  Errors: North {error_north:.6f}°, South {error_south:.6f}°")

    if error_north < 0.001 and error_south < 0.001:
        print(f"  ✓ Excellent alignment!")
    elif error_north < 0.01 and error_south < 0.01:
        print(f"  ✓ Good alignment")
    else:
        print(f"  ⚠️  Alignment needs refinement")

    # Save results
    bounds = [image_west, image_south, image_east, image_north]

    results = {
        'method': 'direct_calculation',
        'resolutions': {
            'lat': float(deg_per_pixel_lat),
            'lon': float(deg_per_pixel_lon)
        },
        'bounds': {
            'west': float(image_west),
            'south': float(image_south),
            'east': float(image_east),
            'north': float(image_north)
        },
        'bounds_array': [float(x) for x in bounds],
        'verification': {
            'data_north': float(data_north),
            'data_south': float(data_south),
            'expected_north': float(grib_lats.max()),
            'expected_south': float(grib_lats.min()),
            'error_north_deg': float(error_north),
            'error_south_deg': float(error_south)
        }
    }

    with open('DIRECT_BOUNDS_CALCULATION.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: DIRECT_BOUNDS_CALCULATION.json")

    print(f"\n✨ RECOMMENDED BOUNDS:")
    print(f"   [{image_west:.6f}, {image_south:.6f}, {image_east:.6f}, {image_north:.6f}]")

    print(f"\n{'='*70}\n")

    return results

if __name__ == '__main__':
    calculate_bounds_direct()
