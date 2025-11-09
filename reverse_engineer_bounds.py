#!/usr/bin/env python3
"""
FRESH START - Reverse Engineer Image Bounds from Pixel Data

Instead of calculating what the bounds SHOULD be, let's figure out what they
actually ARE by examining the images and GRIB2 data together.

Approach:
1. Load the GRIB2 lat/lon grids (919×1299)
2. Load the reprojected images (12170×1200)
3. Find the relationship between GRIB grid points and image pixels
4. Calculate the correct bounds from this relationship
"""

import json
import numpy as np
from PIL import Image

def analyze_image_to_grib_mapping():
    print("="*70)
    print("REVERSE ENGINEERING IMAGE BOUNDS FROM ACTUAL DATA")
    print("="*70)

    # Load GRIB2 lat/lon grids
    grib_lats = np.load('hrrr_ak_latitudes.npy')
    grib_lons = np.load('hrrr_ak_longitudes.npy')

    grib_height, grib_width = grib_lats.shape
    print(f"\n📊 GRIB2 Grid: {grib_height} × {grib_width}")

    # Convert to ±180°
    grib_lons_180 = np.where(grib_lons > 180, grib_lons - 360, grib_lons)

    print(f"   Lat range: {grib_lats.min():.3f}° to {grib_lats.max():.3f}°")
    print(f"   Lon range: {grib_lons_180.min():.3f}° to {grib_lons_180.max():.3f}°")

    # Load image
    img = Image.open('images/alaska_hrrr_western.webp')
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]

    print(f"\n🖼️  Reprojected Image: {img_width} × {img_height}")

    # Find data extent
    if img.mode == 'RGBA':
        alpha = img_array[:, :, 3]
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask = (alpha > 0) & has_color

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

    print(f"   Data extent: rows {data_top}-{data_bottom} ({data_height}px), cols {data_left}-{data_right} ({data_width}px)")

    # KEY INSIGHT: The image width should correspond to 360° (full wrap around)
    # because the images are designed to tile horizontally for dateline wrapping

    # Let's check: what is the longitude span represented by the image width?
    grib_lon_span = grib_lons_180.max() - grib_lons_180.min()
    print(f"\n🌐 GRIB longitude span: {grib_lon_span:.3f}°")

    # If the image is designed to wrap 360°, then:
    deg_per_pixel_lon = 360.0 / img_width
    print(f"   If image wraps 360°: {deg_per_pixel_lon:.6f}° per pixel")

    # But we also know the data width. What span does that represent?
    data_lon_span = grib_lon_span  # The data should span the GRIB extent
    deg_per_pixel_lon_data = data_lon_span / data_width
    print(f"   Based on data width: {deg_per_pixel_lon_data:.6f}° per pixel")

    # For latitude:
    grib_lat_span = grib_lats.max() - grib_lats.min()
    deg_per_pixel_lat = grib_lat_span / data_height

    print(f"\n📏 Calculated resolution:")
    print(f"   Latitude:  {deg_per_pixel_lat:.6f}° per pixel")
    print(f"   Longitude: {deg_per_pixel_lon_data:.6f}° per pixel")

    # Now calculate image bounds
    # The GRIB grid extent should map to the data pixels

    # Latitude bounds:
    # If data_top (pixel 129) should be at grib_lats.max(), then:
    # pixel 0 (image north) = grib_lats.max() + (data_top * deg_per_pixel_lat)
    image_north = grib_lats.max() + (data_top * deg_per_pixel_lat)
    image_south = image_north - (img_height * deg_per_pixel_lat)

    print(f"\n📐 Latitude bounds:")
    print(f"   Image north (pixel 0): {image_north:.6f}°")
    print(f"   Image south (pixel {img_height}): {image_south:.6f}°")
    print(f"   Data north (pixel {data_top}): {grib_lats.max():.6f}° ✓")
    print(f"   Data south (pixel {data_bottom}): {image_north - ((data_bottom+1) * deg_per_pixel_lat):.6f}° (should be {grib_lats.min():.6f}°)")

    # Longitude bounds:
    # The tricky part - the image wraps around
    # Let's assume the image represents a full 360° wrap
    # with the GRIB data centered within it

    # If the image is 360° wide, starting at what longitude?
    # The GRIB data spans from grib_lons_180.min() to grib_lons_180.max()
    # This data occupies pixels data_left to data_right

    # Work backwards: if data_left should be at grib_lons_180.min():
    image_west = grib_lons_180.min() - (data_left * deg_per_pixel_lon_data)
    image_east = image_west + (img_width * deg_per_pixel_lon_data)

    print(f"\n📐 Longitude bounds (assuming data wraps to 360°):")
    print(f"   Image west (pixel 0): {image_west:.6f}°")
    print(f"   Image east (pixel {img_width}): {image_east:.6f}°")
    print(f"   Span: {image_east - image_west:.6f}°")

    # Alternative: assume image is exactly the GRIB extent with padding
    # In this case, the image represents only the GRIB lon span
    deg_per_pixel_lon_alt = grib_lon_span / data_width
    image_west_alt = grib_lons_180.min() - (data_left * deg_per_pixel_lon_alt)
    image_east_alt = image_west_alt + (img_width * deg_per_pixel_lon_alt)

    print(f"\n📐 Longitude bounds (alternative - GRIB span only):")
    print(f"   Image west (pixel 0): {image_west_alt:.6f}°")
    print(f"   Image east (pixel {img_width}): {image_east_alt:.6f}°")
    print(f"   Span: {image_east_alt - image_west_alt:.6f}°")

    # Let's also check: what if the images are meant to be split at dateline?
    # Western image: -180° to some eastern lon
    # Eastern image: some western lon to +180°

    print(f"\n🤔 Dateline split hypothesis:")
    print(f"   GRIB span: {grib_lon_span:.3f}° crossing dateline")
    print(f"   Western part (mainland): -180° to {grib_lons_180.max():.3f}°")
    print(f"   Eastern part (Aleutians): {grib_lons_180.min():.3f}° to +180°")

    # Save results for inspection
    results = {
        'grib_grid': {
            'shape': [int(grib_height), int(grib_width)],
            'lat_range': [float(grib_lats.min()), float(grib_lats.max())],
            'lon_range': [float(grib_lons_180.min()), float(grib_lons_180.max())],
            'lat_span': float(grib_lat_span),
            'lon_span': float(grib_lon_span)
        },
        'image': {
            'shape': [img_height, img_width],
            'data_extent': {
                'top': int(data_top),
                'bottom': int(data_bottom),
                'left': int(data_left),
                'right': int(data_right)
            }
        },
        'calculated_resolutions': {
            'lat': float(deg_per_pixel_lat),
            'lon_360wrap': float(deg_per_pixel_lon),
            'lon_grib_span': float(deg_per_pixel_lon_data)
        },
        'hypothesis_1_360wrap': {
            'bounds': [float(image_west), float(image_south), float(image_east), float(image_north)]
        },
        'hypothesis_2_grib_span_only': {
            'bounds': [float(image_west_alt), float(image_south), float(image_east_alt), float(image_north)]
        }
    }

    with open('REVERSE_ENGINEERING_RESULTS.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: REVERSE_ENGINEERING_RESULTS.json")
    print(f"\n{'='*70}\n")

    return results

if __name__ == '__main__':
    analyze_image_to_grib_mapping()
