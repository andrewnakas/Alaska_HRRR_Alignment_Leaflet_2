#!/usr/bin/env python3
"""
Calculate Grid Cell Center vs Corner Offset

The boundary polygon is offset by ~0.008° from GRIB edges.
This is likely because:
- GRIB2 coordinates are grid CELL CENTERS
- Boundary polygon is grid CELL CORNERS
- Or vice versa

HRRR-Alaska has 3km grid spacing. Let's verify.
"""

import json
import numpy as np

def calculate_offset():
    print("="*70)
    print("GRID CELL CENTER vs CORNER OFFSET")
    print("="*70)

    # Load GRIB2 grid
    grib_lats = np.load('hrrr_ak_latitudes.npy')
    grib_lons = np.load('hrrr_ak_longitudes.npy')

    ny, nx = grib_lats.shape
    print(f"\nGRIB2 grid: {ny} × {nx}")

    # Calculate grid spacing
    # Sample a few points to estimate spacing
    lat_spacing_samples = []
    lon_spacing_samples = []

    # Sample in middle of grid to avoid edge effects
    mid_y = ny // 2
    mid_x = nx // 2

    for i in range(mid_y-10, mid_y+10):
        for j in range(mid_x-10, mid_x+10):
            if i < ny-1:
                lat_diff = abs(grib_lats[i+1, j] - grib_lats[i, j])
                if lat_diff > 0:
                    lat_spacing_samples.append(lat_diff)
            if j < nx-1:
                lon_diff = abs(grib_lons[i, j+1] - grib_lons[i, j])
                if lon_diff > 0:
                    lon_spacing_samples.append(lon_diff)

    avg_lat_spacing = np.mean(lat_spacing_samples)
    avg_lon_spacing = np.mean(lon_spacing_samples)

    print(f"\nAverage grid spacing:")
    print(f"   Latitude:  {avg_lat_spacing:.6f}° (~{avg_lat_spacing * 111:.2f} km)")
    print(f"   Longitude: {avg_lon_spacing:.6f}°")

    # The observed offset
    observed_offset = 0.007922

    print(f"\nObserved boundary offset: {observed_offset:.6f}°")
    print(f"   Distance: ~{observed_offset * 111:.2f} km")

    # Check if it's half a grid cell
    half_cell_lat = avg_lat_spacing / 2
    print(f"\nHalf grid cell (latitude): {half_cell_lat:.6f}°")
    print(f"   Ratio to observed: {observed_offset / half_cell_lat:.3f}")

    if abs(observed_offset - half_cell_lat) / half_cell_lat < 0.1:
        print(f"   ✓ Offset matches HALF a grid cell!")
        print(f"   This confirms: GRIB coords are centers, boundary wants corners")
    else:
        print(f"   ✗ Offset does NOT match half cell")

    # Now let's figure out which way the adjustment should go
    # Load boundary polygon
    with open('test-data.json', 'r') as f:
        data = json.load(f)

    boundary = data['boundary_polygon']
    boundary_lats = [p['lat'] for p in boundary]

    boundary_min_lat = min(boundary_lats)
    boundary_max_lat = max(boundary_lats)

    grib_min_lat = float(grib_lats.min())
    grib_max_lat = float(grib_lats.max())

    print(f"\n📊 Comparison:")
    print(f"   Boundary lat: {boundary_min_lat:.6f}° to {boundary_max_lat:.6f}°")
    print(f"   GRIB lat:     {grib_min_lat:.6f}° to {grib_max_lat:.6f}°")
    print(f"   Boundary is INSIDE GRIB (smaller extent)")

    print(f"\n💡 Interpretation:")
    print(f"   - GRIB coordinates are at grid cell CENTERS")
    print(f"   - Boundary polygon is ALSO at centers (or close to it)")
    print(f"   - For image bounds, we need the CORNERS of the grid cells")
    print(f"   - This means expanding the bounds by half a cell on each side")

    # Calculate corrected bounds
    print(f"\n✨ CORRECTED BOUNDS CALCULATION:")
    print(f"   GRIB min lat: {grib_min_lat:.6f}°")
    print(f"   Subtract half cell: {grib_min_lat - half_cell_lat:.6f}° (image south)")
    print(f"   GRIB max lat: {grib_max_lat:.6f}°")
    print(f"   Add half cell: {grib_max_lat + half_cell_lat:.6f}° (image north)")

    # For our image, which has padding:
    # Data pixels 129-1176 should map to the CELL CORNERS extent
    # Not the cell center extent

    data_top = 129
    data_bottom = 1176
    data_height = data_bottom - data_top + 1

    # GRIB extent WITH half-cell expansion
    grib_north_corner = grib_max_lat + half_cell_lat
    grib_south_corner = grib_min_lat - half_cell_lat
    grib_lat_range_corners = grib_north_corner - grib_south_corner

    deg_per_pixel_lat = grib_lat_range_corners / data_height

    image_north = grib_north_corner + (data_top * deg_per_pixel_lat)
    image_south = grib_north_corner - ((data_bottom + 1) * deg_per_pixel_lat)

    print(f"\n📐 With half-cell correction:")
    print(f"   GRIB corners extent: {grib_south_corner:.6f}° to {grib_north_corner:.6f}°")
    print(f"   Range: {grib_lat_range_corners:.6f}°")
    print(f"   Deg/pixel: {deg_per_pixel_lat:.6f}° per pixel")
    print(f"\n   Image bounds:")
    print(f"   North: {image_north:.6f}°")
    print(f"   South: {image_south:.6f}°")

    # For longitude (similar logic)
    grib_lons_180 = np.where(grib_lons > 180, grib_lons - 360, grib_lons)

    # Estimate lon spacing at center
    mid_lon_spacing_samples = []
    for i in range(mid_y-10, mid_y+10):
        for j in range(mid_x-10, mid_x+10):
            if j < nx-1:
                lon_diff = abs(grib_lons_180[i, j+1] - grib_lons_180[i, j])
                if 0 < lon_diff < 1:  # Filter out dateline wraps
                    mid_lon_spacing_samples.append(lon_diff)

    avg_lon_spacing_mid = np.mean(mid_lon_spacing_samples)
    half_cell_lon = avg_lon_spacing_mid / 2

    grib_west = float(grib_lons_180.min())
    grib_east = float(grib_lons_180.max())

    print(f"\n   Longitude (with padding would be full 360°):")
    print(f"   GRIB extent: {grib_west:.6f}° to {grib_east:.6f}°")
    print(f"   With half-cell: {grib_west - half_cell_lon:.6f}° to {grib_east + half_cell_lon:.6f}°")

    # Save results
    results = {
        'grid_spacing': {
            'lat': float(avg_lat_spacing),
            'lon': float(avg_lon_spacing),
            'lat_km': float(avg_lat_spacing * 111),
        },
        'half_cell': {
            'lat': float(half_cell_lat),
            'lon': float(half_cell_lon)
        },
        'observed_offset': float(observed_offset),
        'offset_is_half_cell': abs(observed_offset - half_cell_lat) / half_cell_lat < 0.1,
        'corrected_grib_extent_corners': {
            'lat': [float(grib_south_corner), float(grib_north_corner)],
            'lon': [float(grib_west - half_cell_lon), float(grib_east + half_cell_lon)]
        },
        'recommended_image_bounds': {
            'north': float(image_north),
            'south': float(image_south),
            'west': float(grib_west - half_cell_lon),
            'east': float(grib_east + half_cell_lon)
        }
    }

    with open('GRID_CELL_OFFSET_ANALYSIS.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Saved to: GRID_CELL_OFFSET_ANALYSIS.json")
    print(f"\n{'='*70}\n")

    return results

if __name__ == '__main__':
    calculate_offset()
