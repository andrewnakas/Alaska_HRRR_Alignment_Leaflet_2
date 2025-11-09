#!/usr/bin/env python3
"""
Split Bounds for Date Line Crossing

The HRRR-Alaska domain crosses the date line:
- Eastern hemisphere: 156.437°E to 180°E
- Western hemisphere: -180°W to -115.776°W

The two images need different bounds to align correctly.
"""

import json
import numpy as np
from PIL import Image

def analyze_dateline_split():
    print("="*70)
    print("DATE LINE SPLIT ANALYSIS")
    print("="*70)

    # GRIB bounding box (from corners)
    bbox_north = 76.337657
    bbox_south = 41.612949
    bbox_east_360 = 244.224263  # In 0-360° format
    bbox_west_360 = 156.436843  # In 0-360° format

    # Convert to ±180°
    bbox_east = bbox_east_360 - 360  # 244.224 - 360 = -115.776°
    bbox_west = bbox_west_360         # 156.437°

    total_lon_span = bbox_east_360 - bbox_west_360  # 87.787°

    print(f"\n📦 Full Domain:")
    print(f"   Latitude:  {bbox_south:.3f}° to {bbox_north:.3f}°")
    print(f"   Longitude: {bbox_west:.3f}° to {bbox_east:.3f}° (crosses ±180°)")
    print(f"   Total span: {total_lon_span:.3f}°")

    # The domain crosses the dateline
    # Eastern part: 156.437° to 180°
    # Western part: -180° to -115.776°

    eastern_lon_span = 180 - bbox_west  # 180 - 156.437 = 23.563°
    western_lon_span = bbox_east - (-180)  # -115.776 - (-180) = 64.224°

    print(f"\n🌐 Date Line Split:")
    print(f"   Eastern hemisphere: {bbox_west:.3f}° to 180.0° ({eastern_lon_span:.3f}°)")
    print(f"   Western hemisphere: -180.0° to {bbox_east:.3f}° ({western_lon_span:.3f}°)")
    print(f"   Total: {eastern_lon_span + western_lon_span:.3f}° ✓")

    # Load images to determine which is which
    img_west = Image.open('images/alaska_hrrr_western.webp')
    img_east = Image.open('images/alaska_hrrr_eastern.webp')

    width_west = img_west.size[0]
    width_east = img_east.size[0]

    print(f"\n🖼️  Images:")
    print(f"   Western: {width_west} px wide")
    print(f"   Eastern: {width_east} px wide")

    # Find data extent in images
    img_west_array = np.array(img_west)
    img_east_array = np.array(img_east)

    # Analyze western image
    if img_west.mode == 'RGBA':
        a = img_west_array[:, :, 3]
        r, g, b = img_west_array[:,:,0], img_west_array[:,:,1], img_west_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask_west = (a > 0) & has_color

    rows_west = np.any(data_mask_west, axis=1)
    cols_west = np.any(data_mask_west, axis=0)

    row_indices_west = np.where(rows_west)[0]
    col_indices_west = np.where(cols_west)[0]

    data_top = row_indices_west[0]
    data_bottom = row_indices_west[-1]
    data_height = data_bottom - data_top + 1

    data_left_west = col_indices_west[0]
    data_right_west = col_indices_west[-1]
    data_width_west = data_right_west - data_left_west + 1

    print(f"\n📍 Western image data extent:")
    print(f"   Columns: {data_left_west} to {data_right_west} ({data_width_west} pixels)")
    print(f"   Rows: {data_top} to {data_bottom} ({data_height} pixels)")

    # Analyze eastern image
    if img_east.mode == 'RGBA':
        a = img_east_array[:, :, 3]
        r, g, b = img_east_array[:,:,0], img_east_array[:,:,1], img_east_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask_east = (a > 0) & has_color

    cols_east = np.any(data_mask_east, axis=0)
    col_indices_east = np.where(cols_east)[0]

    data_left_east = col_indices_east[0]
    data_right_east = col_indices_east[-1]
    data_width_east = data_right_east - data_left_east + 1

    print(f"\n📍 Eastern image data extent:")
    print(f"   Columns: {data_left_east} to {data_right_east} ({data_width_east} pixels)")

    # The images are the full width - they span the entire domain
    # We need to assign proper longitude bounds to each

    # Calculate latitude bounds (same for both images)
    lat_range = bbox_north - bbox_south
    deg_per_pixel_lat = lat_range / data_height

    image_north = bbox_north + (data_top * deg_per_pixel_lat)
    image_south = bbox_north - ((data_bottom + 1) * deg_per_pixel_lat)

    # The full data width represents the total longitude span
    deg_per_pixel_lon = total_lon_span / data_width_west

    print(f"\n📏 Resolution:")
    print(f"   Latitude:  {deg_per_pixel_lat:.6f}° per pixel")
    print(f"   Longitude: {deg_per_pixel_lon:.6f}° per pixel")

    # Both images contain the full domain, but we display them at different longitude offsets
    # to handle the dateline wrapping

    # Western image: shows the western hemisphere part
    # In Leaflet, we'll use bounds in ±180° range
    western_bounds = [
        -180.0,              # West edge
        image_south,         # South
        bbox_east,           # East edge (-115.776°)
        image_north          # North
    ]

    # Eastern image: shows the eastern hemisphere part
    eastern_bounds = [
        bbox_west,           # West edge (156.437°)
        image_south,         # South
        180.0,               # East edge
        image_north          # North
    ]

    print(f"\n✨ CORRECTED BOUNDS:")
    print(f"\nWestern image (shows Alaska mainland):")
    print(f"   [{western_bounds[0]:.6f}, {western_bounds[1]:.6f}, {western_bounds[2]:.6f}, {western_bounds[3]:.6f}]")
    print(f"   Span: {western_bounds[2] - western_bounds[0]:.3f}° longitude")

    print(f"\nEastern image (shows Aleutians/western islands):")
    print(f"   [{eastern_bounds[0]:.6f}, {eastern_bounds[1]:.6f}, {eastern_bounds[2]:.6f}, {eastern_bounds[3]:.6f}]")
    print(f"   Span: {eastern_bounds[2] - eastern_bounds[0]:.3f}° longitude")

    # Save results
    result = {
        'western': {
            'bounds': western_bounds,
            'description': 'Western hemisphere (Alaska mainland): -180° to -115.8°W'
        },
        'eastern': {
            'bounds': eastern_bounds,
            'description': 'Eastern hemisphere (Aleutians): 156.4°E to 180°E'
        }
    }

    with open('DATELINE_SPLIT_BOUNDS.json', 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Saved to: DATELINE_SPLIT_BOUNDS.json")
    print(f"\n{'='*70}\n")

    return result


if __name__ == '__main__':
    analyze_dateline_split()
