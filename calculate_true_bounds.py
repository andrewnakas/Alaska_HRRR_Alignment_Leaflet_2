#!/usr/bin/env python3
"""
Calculate TRUE Bounding Box from Curved Polar Stereographic Corners

The GRIB2 corners don't form a rectangle - they're curved in polar stereographic.
We need to find the rectangular bounding box that contains all the corners.

GRIB2 Corners (from actual data):
  NW: (41.613°, 185.117°)
  NE: (51.726°, 231.527°)
  SW: (55.605°, 156.437°)
  SE: (76.338°, 244.224°)

For a proper Leaflet imageOverlay, we need:
  - North = max(all latitudes) = 76.338°
  - South = min(all latitudes) = 41.613°
  - East = max(all longitudes) = 244.224°
  - West = min(all longitudes) = 156.437°
"""

import json
import numpy as np
from PIL import Image

def calculate_true_bounds():
    print("="*70)
    print("TRUE Bounding Box from GRIB2 Corners")
    print("="*70)

    # Load GRIB2 corners
    with open('hrrr_ak_grid_info.json', 'r') as f:
        grib_info = json.load(f)

    corners = grib_info['corners']

    print(f"\nGRIB2 Grid Corners (from actual data):")
    for name, coord in corners.items():
        lat, lon = coord['lat'], coord['lon']
        lon_180 = lon - 360 if lon > 180 else lon
        print(f"  {name}: lat={lat:7.3f}°, lon={lon:7.3f}° ({lon_180:+7.2f}°)")

    # Calculate bounding box
    lats = [c['lat'] for c in corners.values()]
    lons = [c['lon'] for c in corners.values()]

    bbox_north = max(lats)
    bbox_south = min(lats)
    bbox_east = max(lons)
    bbox_west = min(lons)

    print(f"\n📦 Rectangular Bounding Box:")
    print(f"  North: {bbox_north:.6f}°")
    print(f"  South: {bbox_south:.6f}°")
    print(f"  East:  {bbox_east:.6f}°")
    print(f"  West:  {bbox_west:.6f}°")

    # Convert to -180 to +180 range
    west_180 = bbox_west - 360 if bbox_west > 180 else bbox_west
    east_180 = bbox_east - 360 if bbox_east > 180 else bbox_east

    print(f"\n📦 In ±180° format:")
    print(f"  West:  {west_180:.6f}°")
    print(f"  South: {bbox_south:.6f}°")
    print(f"  East:  {east_180:.6f}°")
    print(f"  North: {bbox_north:.6f}°")

    # Load image to see how data fits
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

    print(f"\n🖼️  Image Analysis:")
    print(f"  Image size: {width} × {height} pixels")
    print(f"  Data pixels: rows {data_top} to {data_bottom} ({data_height} pixels)")

    # The image should span the bounding box
    # But the data only fills part of it (the curved polar shape)

    # Calculate what bounds would make the bbox align with the image
    lat_range = bbox_north - bbox_south  # 34.725°
    lon_range = bbox_east - bbox_west     # 87.787°

    # If data occupies pixels data_top to data_bottom,
    # and that should map to bbox_south to bbox_north,
    # then we can calculate the image bounds

    deg_per_pixel_lat = lat_range / data_height
    deg_per_pixel_lon = lon_range / width

    print(f"\n📏 Degrees per pixel (bbox / data extent):")
    print(f"  Latitude:  {deg_per_pixel_lat:.6f}° per pixel")
    print(f"  Longitude: {deg_per_pixel_lon:.6f}° per pixel")

    # Calculate image bounds
    image_north = bbox_north + (data_top * deg_per_pixel_lat)
    image_south = bbox_north - ((data_bottom + 1) * deg_per_pixel_lat)
    image_west = bbox_west
    image_east = bbox_east

    print(f"\n✨ RECOMMENDED Image Bounds for Leaflet:")
    print(f"  North: {image_north:.6f}°")
    print(f"  South: {image_south:.6f}°")
    print(f"  West:  {image_west:.6f}°")
    print(f"  East:  {image_east:.6f}°")

    # In -180 to +180 format
    image_west_180 = image_west - 360 if image_west > 180 else image_west
    image_east_180 = image_east - 360 if image_east > 180 else image_east

    print(f"\n✨ In ±180° format:")
    print(f"  [{image_west_180:.6f}, {image_south:.6f}, {image_east_180:.6f}, {image_north:.6f}]")

    # Verification
    print(f"\n🔍 Verification:")
    bbox_north_pixel = (image_north - bbox_north) / deg_per_pixel_lat
    bbox_south_pixel = (image_north - bbox_south) / deg_per_pixel_lat

    print(f"  BBox north ({bbox_north:.3f}°) -> pixel {bbox_north_pixel:.1f} (data starts at {data_top})")
    print(f"  BBox south ({bbox_south:.3f}°) -> pixel {bbox_south_pixel:.1f} (data ends at {data_bottom})")

    # Save results
    results = {
        'grib_corners': corners,
        'bounding_box': {
            'north': bbox_north,
            'south': bbox_south,
            'east': bbox_east,
            'west': bbox_west
        },
        'recommended_image_bounds': {
            'north': image_north,
            'south': image_south,
            'east': image_east,
            'west': image_west
        },
        'recommended_bounds_180': [image_west_180, image_south, image_east_180, image_north]
    }

    with open('true_bounds_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📝 Results saved to: true_bounds_analysis.json")
    print(f"\n{'='*70}\n")

    return results


if __name__ == '__main__':
    calculate_true_bounds()
