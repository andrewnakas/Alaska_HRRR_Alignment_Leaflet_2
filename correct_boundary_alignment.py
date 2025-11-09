#!/usr/bin/env python3
"""
CORRECT Boundary Alignment Calculation

The boundary polygon (41.621° to 77.085°) represents the TRUE extent of
the HRRR-Alaska domain. The colored radar data pixels contain this domain.

We need to calculate what the IMAGE bounds should be so that when we map
the boundary polygon coordinates to pixels, they align with where the
actual radar data is.

Logic:
1. Boundary polygon spans 41.621° to 77.085° (35.464° latitude)
2. Radar data occupies pixels 129-1176 (1048 pixels)
3. Therefore: deg/pixel = 35.464 / 1048 = 0.033836° per pixel
4. If pixel 129 is at 77.085° and pixel 1176 is at 41.621°,
   then pixel 0 (image north) = 77.085 + (129 × 0.033836)
   and pixel 1200 (image south) = 41.621 - (24 × 0.033836)

Usage:
    python3 correct_boundary_alignment.py
"""

import json
import numpy as np
from PIL import Image

def calculate_correct_bounds(image_path, boundary_polygon, stated_bounds, label):
    """
    Calculate what the image bounds SHOULD be to align boundary with data.

    The boundary polygon defines the TRUE geographic extent. We need to
    find what image bounds make the boundary align with the actual radar pixels.
    """
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

    # Load image and find radar data extent
    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]

    print(f"Image: {width} × {height} pixels")

    # Find actual radar data pixels (alpha > 0 with significant color)
    if img.mode == 'RGBA':
        r, g, b, a = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2], img_array[:,:,3]
        has_alpha = a > 0
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask = has_alpha & has_color
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

    print(f"\nRadar data extent:")
    print(f"  Rows: {data_top} to {data_bottom} ({data_height} pixels)")
    print(f"  Cols: {data_left} to {data_right} ({data_width} pixels)")

    # Get boundary polygon extent
    lats = [p['lat'] for p in boundary_polygon]
    lons = [p['lon'] for p in boundary_polygon]

    boundary_south = min(lats)
    boundary_north = max(lats)
    boundary_west = min(lons)
    boundary_east = max(lons)

    boundary_lat_range = boundary_north - boundary_south
    boundary_lon_range = boundary_east - boundary_west

    print(f"\nBoundary polygon extent:")
    print(f"  Latitude: {boundary_south:.6f}° to {boundary_north:.6f}° ({boundary_lat_range:.6f}°)")
    print(f"  Longitude: {boundary_west:.6f}° to {boundary_east:.6f}° ({boundary_lon_range:.6f}°)")

    # Calculate deg/pixel based on boundary range fitting into data pixels
    deg_per_pixel_lat = boundary_lat_range / data_height
    deg_per_pixel_lon = boundary_lon_range / data_width

    print(f"\nDegrees per pixel (based on boundary fitting data):")
    print(f"  Latitude:  {deg_per_pixel_lat:.6f}° per pixel")
    print(f"  Longitude: {deg_per_pixel_lon:.6f}° per pixel")

    # Calculate image bounds
    # If data_top (e.g., pixel 129) should be at boundary_north (77.085°),
    # then pixel 0 (image north) = boundary_north + (data_top × deg_per_pixel_lat)

    image_north = boundary_north + (data_top * deg_per_pixel_lat)
    image_south = boundary_north - ((data_bottom + 1) * deg_per_pixel_lat)

    # Alternative calculation for south (should give same result):
    # image_south = boundary_south - ((height - data_bottom - 1) * deg_per_pixel_lat)

    image_west = boundary_west - (data_left * deg_per_pixel_lon)
    image_east = boundary_west + ((data_right + 1) * deg_per_pixel_lon)

    print(f"\n✨ CORRECTED Image Bounds:")
    print(f"  North: {image_north:.6f}°")
    print(f"  South: {image_south:.6f}°")
    print(f"  West:  {image_west:.6f}°")
    print(f"  East:  {image_east:.6f}°")
    print(f"  Lat range: {image_north - image_south:.6f}°")
    print(f"  Lon range: {image_east - image_west:.6f}°")

    # Verify: map boundary polygon to pixels with these bounds
    print(f"\n🔍 Verification - Boundary polygon should map to data pixels:")

    # Map boundary north point to pixels
    boundary_north_pixel = (image_north - boundary_north) / deg_per_pixel_lat
    boundary_south_pixel = (image_north - boundary_south) / deg_per_pixel_lat

    print(f"  Boundary north ({boundary_north:.3f}°) -> pixel {boundary_north_pixel:.1f} (data starts at {data_top})")
    print(f"  Boundary south ({boundary_south:.3f}°) -> pixel {boundary_south_pixel:.1f} (data ends at {data_bottom})")

    # Compare to stated bounds
    west_stated, south_stated, east_stated, north_stated = stated_bounds
    print(f"\n📊 Comparison to stated bounds:")
    print(f"  North: {north_stated:.6f}° -> {image_north:.6f}° (change: {image_north - north_stated:+.6f}°)")
    print(f"  South: {south_stated:.6f}° -> {image_south:.6f}° (change: {image_south - south_stated:+.6f}°)")
    print(f"  West:  {west_stated:.6f}° -> {image_west:.6f}° (change: {image_west - west_stated:+.6f}°)")
    print(f"  East:  {east_stated:.6f}° -> {image_east:.6f}° (change: {image_east - east_stated:+.6f}°)")

    return {
        'image_bounds': [image_west, image_south, image_east, image_north],
        'boundary_extent': {
            'south': boundary_south,
            'north': boundary_north,
            'west': boundary_west,
            'east': boundary_east
        },
        'data_pixels': {
            'top': int(data_top),
            'bottom': int(data_bottom),
            'left': int(data_left),
            'right': int(data_right),
            'height': int(data_height),
            'width': int(data_width)
        },
        'deg_per_pixel': {
            'lat': deg_per_pixel_lat,
            'lon': deg_per_pixel_lon
        }
    }


def main():
    """Main analysis."""
    print("="*70)
    print("CORRECT Boundary Alignment Calculation")
    print("="*70)

    # Load data
    with open('test-data.json', 'r') as f:
        data = json.load(f)

    boundary_polygon = data['boundary_polygon']

    # Analyze western image
    western_result = calculate_correct_bounds(
        'images/alaska_hrrr_western.webp',
        boundary_polygon,
        data['western']['bounds'],
        'Western Image'
    )

    # Analyze eastern image
    eastern_result = calculate_correct_bounds(
        'images/alaska_hrrr_eastern.webp',
        boundary_polygon,
        data['eastern']['bounds'],
        'Eastern Image'
    )

    # Recommendation
    print(f"\n{'='*70}")
    print("RECOMMENDATION")
    print(f"{'='*70}")

    print(f"\n✅ Update test-data.json with these bounds:")
    print(f"\n  Western: {western_result['image_bounds']}")
    print(f"  Eastern: {eastern_result['image_bounds']}")

    print(f"\nThese bounds ensure the boundary polygon (41.621° to 77.085°)")
    print(f"aligns precisely with the radar data pixels in the images.")

    # Save results
    results = {
        'western': western_result,
        'eastern': eastern_result
    }

    with open('correct_alignment_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📝 Results saved to: correct_alignment_results.json")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
