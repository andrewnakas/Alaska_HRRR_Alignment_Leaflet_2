#!/usr/bin/env python3
"""
Compare GRIB2 Grid to Reprojected Images

Now that we have the TRUE HRRR-Alaska grid from GRIB2,
let's figure out how it maps to the reprojected images.

The GRIB2 grid is 919×1299 in polar stereographic projection.
The images are 1200×12170 in WGS84 (lat/lon) projection.

We need to understand this transformation.

Usage:
    python3 analyze_grib_vs_images.py
"""

import json
import numpy as np
from PIL import Image

def main():
    print("="*70)
    print("GRIB2 Grid vs Reprojected Images Analysis")
    print("="*70)

    # Load GRIB2 grid info
    with open('hrrr_ak_grid_info.json', 'r') as f:
        grib_info = json.load(f)

    print(f"\n📊 GRIB2 Grid (Native Polar Stereographic):")
    print(f"   Dimensions: {grib_info['grid_dimensions']['ny']} × {grib_info['grid_dimensions']['nx']}")
    print(f"   Latitude:  {grib_info['geographic_extent']['lat_min']:.6f}° to {grib_info['geographic_extent']['lat_max']:.6f}°")
    print(f"   Longitude: {grib_info['geographic_extent']['lon_min']:.6f}° to {grib_info['geographic_extent']['lon_max']:.6f}°")

    # Load lat/lon grids
    lats = np.load('hrrr_ak_latitudes.npy')
    lons = np.load('hrrr_ak_longitudes.npy')

    print(f"\n🌍 Geographic Coverage:")
    print(f"   Lat range: {lats.min():.6f}° to {lats.max():.6f}° ({lats.max() - lats.min():.6f}°)")
    print(f"   Lon range: {lons.min():.6f}° to {lons.max():.6f}°")

    # Convert longitudes to -180 to +180 range
    lons_180 = np.where(lons > 180, lons - 360, lons)
    print(f"   Lon range (±180): {lons_180.min():.6f}° to {lons_180.max():.6f}°")

    # Check if it crosses date line
    crosses_dateline = lons.min() < 180 and lons.max() > 180
    print(f"   Crosses date line: {crosses_dateline}")

    # Load image to see dimensions
    img_western = Image.open('images/alaska_hrrr_western.webp')
    img_eastern = Image.open('images/alaska_hrrr_eastern.webp')

    print(f"\n🖼️  Reprojected Images (WGS84):")
    print(f"   Western: {img_western.size[0]} × {img_western.size[1]} pixels")
    print(f"   Eastern: {img_eastern.size[0]} × {img_eastern.size[1]} pixels")

    # Find data extent in western image
    img_array = np.array(img_western)
    if img_western.mode == 'RGBA':
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

    print(f"\n📍 Data extent in western image:")
    print(f"   Rows: {data_top} to {data_bottom} ({data_height} pixels)")
    print(f"   Cols: {data_left} to {data_right} ({data_width} pixels)")

    # Key insight: The GRIB2 grid is 919×1299
    # The reprojected data height is ~1048 pixels
    # This suggests some interpolation/resampling happened

    print(f"\n🔍 Size comparison:")
    print(f"   GRIB2 grid: 919 × 1299")
    print(f"   Image data: {data_height} × {data_width}")
    print(f"   Ratio Y: {data_height / 919:.3f}")
    print(f"   Ratio X: {data_width / 1299:.3f}")

    # The key question: What are the CORRECT bounds for the images?
    #
    # The images should have bounds that make the GRIB2 lat/lon grid
    # map correctly to the image pixels.

    print(f"\n{'='*70}")
    print("KEY INSIGHT")
    print(f"{'='*70}")

    # The GRIB2 has lat/lon for every grid point (919×1299)
    # When reprojected to WGS84, it becomes a different size image
    #
    # The image bounds should be:
    # [min_lon, min_lat, max_lon, max_lat] from the GRIB2 grid

    # But we need to split at date line for western/eastern

    # Western hemisphere: lons from 180° to 360° (or -180° to 0°)
    # Eastern hemisphere: lons from 0° to 180°

    # Find which GRIB points are in western vs eastern hemisphere
    western_mask = lons_180 < 0  # Negative longitudes (western hemisphere)
    eastern_mask = lons_180 >= 0  # Positive longitudes (eastern hemisphere)

    if np.any(western_mask):
        western_lats = lats[western_mask]
        western_lons = lons_180[western_mask]
        print(f"\n📍 Western hemisphere coverage:")
        print(f"   Lat: {western_lats.min():.6f}° to {western_lats.max():.6f}°")
        print(f"   Lon: {western_lons.min():.6f}° to {western_lons.max():.6f}°")

    if np.any(eastern_mask):
        eastern_lats = lats[eastern_mask]
        eastern_lons = lons_180[eastern_mask]
        print(f"\n📍 Eastern hemisphere coverage:")
        print(f"   Lat: {eastern_lats.min():.6f}° to {eastern_lats.max():.6f}°")
        print(f"   Lon: {eastern_lons.min():.6f}° to {eastern_lons.max():.6f}°")

    # The CORRECT bounds for Leaflet should be the GRIB2 extent
    print(f"\n{'='*70}")
    print("RECOMMENDED BOUNDS")
    print(f"{'='*70}")

    print(f"\nFor the ENTIRE domain (if using a single image):")
    print(f"  [west, south, east, north]:")
    print(f"  [{lons_180.min():.6f}, {lats.min():.6f}, {lons_180.max():.6f}, {lats.max():.6f}]")

    # But for western/eastern split, we need to wrap around date line
    # Western image covers -180° to eastern edge
    # Eastern image covers western edge to +180°

    print(f"\nFor date-line wrapping (western/eastern split):")

    # Find the eastern-most western longitude and western-most eastern longitude
    western_east = western_lons.max()
    eastern_west = eastern_lons.min()

    # Western image: wraps from -180° to cross date line
    print(f"  Western: [-180.0, {lats.min():.6f}, {western_east:.6f}, {lats.max():.6f}]")
    print(f"  Eastern: [{eastern_west:.6f}, {lats.min():.6f}, 180.0, {lats.max():.6f}]")

    # Save results
    results = {
        'grib2_grid': {
            'dimensions': grib_info['grid_dimensions'],
            'lat_range': [float(lats.min()), float(lats.max())],
            'lon_range': [float(lons.min()), float(lons.max())],
            'lon_range_180': [float(lons_180.min()), float(lons_180.max())]
        },
        'reprojected_image': {
            'dimensions': {'width': img_western.size[0], 'height': img_western.size[1]},
            'data_extent': {
                'top': int(data_top),
                'bottom': int(data_bottom),
                'left': int(data_left),
                'right': int(data_right),
                'width': int(data_width),
                'height': int(data_height)
            }
        },
        'recommended_bounds': {
            'full_domain': [float(lons_180.min()), float(lats.min()), float(lons_180.max()), float(lats.max())],
            'western': [-180.0, float(lats.min()), float(western_east), float(lats.max())],
            'eastern': [float(eastern_west), float(lats.min()), 180.0, float(lats.max())]
        }
    }

    with open('grib_vs_images_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📝 Analysis saved to: grib_vs_images_analysis.json")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
