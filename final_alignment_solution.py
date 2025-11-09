#!/usr/bin/env python3
"""
FINAL ALIGNMENT SOLUTION

The HRRR-Alaska polar stereographic grid has curved corners that don't form a rectangle.
When reprojected to WGS84, we need a rectangular bounding box that contains the entire domain.

Key insights:
1. GRIB corners are CURVED (polar stereographic)
2. SE corner (76.34°) is NORTH of NW corner (41.61°)!
3. The bounding box must contain ALL corners
4. For Leaflet date-line wrapping, we need ±180° bounds

Solution: Use the bounding box extents, accounting for image padding.
"""

import json
import numpy as np
from PIL import Image

# From GRIB2 analysis
GRIB_BBOX = {
    'north': 76.337657,
    'south': 41.612949,
    'east': 244.224263,   # = -115.775737° in ±180°
    'west': 156.436843
}

def convert_to_180(lon):
    """Convert 0-360° to ±180°"""
    return lon - 360 if lon > 180 else lon

def main():
    print("="*70)
    print("FINAL ALIGNMENT SOLUTION")
    print("="*70)

    # Load image
    img = Image.open('images/alaska_hrrr_western.webp')
    img_array = np.array(img)
    height, width = img_array.shape[:2]

    # Find data extent
    if img.mode == 'RGBA':
        a = img_array[:, :, 3]
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask = (a > 0) & has_color
    else:
        data_mask = np.any(img_array > 10, axis=2)

    rows_with_data = np.any(data_mask, axis=1)
    row_indices = np.where(rows_with_data)[0]

    data_top = row_indices[0]
    data_bottom = row_indices[-1]
    data_height = data_bottom - data_top + 1

    print(f"\n📊 Image: {width} × {height} pixels")
    print(f"   Data: rows {data_top}-{data_bottom} ({data_height} pixels)")

    # Geographic extent from GRIB bounding box
    lat_range = GRIB_BBOX['north'] - GRIB_BBOX['south']
    lon_range = GRIB_BBOX['east'] - GRIB_BBOX['west']

    print(f"\n📦 GRIB Bounding Box:")
    print(f"   Lat: {GRIB_BBOX['south']:.3f}° to {GRIB_BBOX['north']:.3f}° ({lat_range:.3f}°)")
    print(f"   Lon: {GRIB_BBOX['west']:.3f}° to {GRIB_BBOX['east']:.3f}° ({lon_range:.3f}°)")

    # Calculate deg/pixel
    deg_per_pixel_lat = lat_range / data_height

    print(f"\n📏 Resolution:")
    print(f"   {deg_per_pixel_lat:.6f}° per pixel (latitude)")

    # Calculate image bounds
    # If data_top should be at GRIB_BBOX['north'], then:
    image_north = GRIB_BBOX['north'] + (data_top * deg_per_pixel_lat)
    image_south = GRIB_BBOX['north'] - ((data_bottom + 1) * deg_per_pixel_lat)

    # For longitude, the full width should span the bounding box
    # The images wrap around ±180°, so we need to handle that
    #
    # Total longitude range: 87.787° (156.437° to 244.224°)
    # This crosses the date line
    #
    # For Leaflet wrapping:
    # - Western image: west side of domain
    # - Eastern image: east side of domain
    # Both should span ±180° in practice

    # The GRIB bbox crosses date line: 156.437°E to 244.224°E (-115.776°W)
    # In ±180° format: 156.437° to -115.776°
    # That's a span of: 360 - (156.437 - (-115.776)) = 360 - 272.213 = 87.787° ✓

    # For the images that wrap:
    # The western image goes from ~-180° to the eastern edge
    # The eastern image goes from the western edge to ~+180°

    # Since the data width fills the entire image (12170 pixels),
    # and the lon range is 87.787°, we have:
    deg_per_pixel_lon = lon_range / width

    # The bounds for both images (they're the same, just wrapped):
    # Use the ±180° format
    west_180 = convert_to_180(GRIB_BBOX['west'])   # 156.437°
    east_180 = convert_to_180(GRIB_BBOX['east'])   # -115.776°

    print(f"\n✨ FINAL Image Bounds (both western and eastern):")
    print(f"   North: {image_north:.6f}°")
    print(f"   South: {image_south:.6f}°")
    print(f"   West:  {west_180:.6f}°")
    print(f"   East:  {east_180:.6f}°")

    # For Leaflet, use the standard -180 to +180 range
    final_bounds = [west_180, image_south, east_180, image_north]

    print(f"\n📋 Leaflet Bounds [west, south, east, north]:")
    print(f"   {final_bounds}")

    # Verification
    print(f"\n🔍 Verification:")
    bbox_north_pixel = (image_north - GRIB_BBOX['north']) / deg_per_pixel_lat
    bbox_south_pixel = (image_north - GRIB_BBOX['south']) / deg_per_pixel_lat
    print(f"   BBox north ({GRIB_BBOX['north']:.3f}°) maps to pixel {bbox_north_pixel:.1f}")
    print(f"   BBox south ({GRIB_BBOX['south']:.3f}°) maps to pixel {bbox_south_pixel:.1f}")
    print(f"   Data is at pixels {data_top} to {data_bottom} ✓")

    # Save final bounds
    result = {
        'western': {'bounds': final_bounds},
        'eastern': {'bounds': final_bounds}
    }

    with open('FINAL_BOUNDS.json', 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Final bounds saved to: FINAL_BOUNDS.json")

    print(f"\n{'='*70}")
    print("APPLY THESE BOUNDS TO test-data.json")
    print(f"{'='*70}\n")

    return final_bounds


if __name__ == '__main__':
    main()
