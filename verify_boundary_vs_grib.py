#!/usr/bin/env python3
"""
Verify Boundary Polygon vs GRIB2 Grid Edges

The boundary polygon should trace the edge of the GRIB2 grid.
Let's verify if it actually does.
"""

import json
import numpy as np

def verify_boundary():
    print("="*70)
    print("VERIFY BOUNDARY POLYGON vs GRIB2 GRID EDGES")
    print("="*70)

    # Load boundary polygon from test-data.json
    with open('test-data.json', 'r') as f:
        data = json.load(f)

    boundary = data['boundary_polygon']
    print(f"\nBoundary polygon: {len(boundary)} points")

    boundary_lats = [p['lat'] for p in boundary]
    boundary_lons = [p['lon'] for p in boundary]

    print(f"   Lat range: {min(boundary_lats):.6f}° to {max(boundary_lats):.6f}°")
    print(f"   Lon range: {min(boundary_lons):.6f}° to {max(boundary_lons):.6f}°")

    # Load GRIB2 grid edges
    grib_lats = np.load('hrrr_ak_latitudes.npy')
    grib_lons = np.load('hrrr_ak_longitudes.npy')

    print(f"\nGRIB2 grid: {grib_lats.shape}")
    print(f"   Lat range: {grib_lats.min():.6f}° to {grib_lats.max():.6f}°")
    print(f"   Lon range: {grib_lons.min():.6f}° to {grib_lons.max():.6f}°")

    # Convert GRIB lons to ±180°
    grib_lons_180 = np.where(grib_lons > 180, grib_lons - 360, grib_lons)
    print(f"   Lon range (±180°): {grib_lons_180.min():.6f}° to {grib_lons_180.max():.6f}°")

    # Extract GRIB2 edge points
    # Top edge (row 0)
    # Right edge (last column)
    # Bottom edge (last row)
    # Left edge (first column)

    ny, nx = grib_lats.shape

    top_edge = [(grib_lats[0, i], grib_lons_180[0, i]) for i in range(nx)]
    right_edge = [(grib_lats[i, -1], grib_lons_180[i, -1]) for i in range(ny)]
    bottom_edge = [(grib_lats[-1, i], grib_lons_180[-1, i]) for i in range(nx-1, -1, -1)]
    left_edge = [(grib_lats[i, 0], grib_lons_180[i, 0]) for i in range(ny-1, -1, -1)]

    grib_edge_points = top_edge + right_edge + bottom_edge + left_edge
    print(f"\nGRIB2 edge: {len(grib_edge_points)} points (full perimeter)")

    # Compare boundary polygon to GRIB edge
    print(f"\n🔍 Comparing boundary polygon to GRIB2 edges:")

    # Sample some boundary points and find nearest GRIB edge point
    sample_indices = [0, len(boundary)//4, len(boundary)//2, 3*len(boundary)//4, -1]

    for idx in sample_indices:
        b_lat = boundary_lats[idx]
        b_lon = boundary_lons[idx]

        # Find closest GRIB edge point
        min_dist = float('inf')
        closest_grib = None

        for g_lat, g_lon in grib_edge_points:
            dist = np.sqrt((b_lat - g_lat)**2 + (b_lon - g_lon)**2)
            if dist < min_dist:
                min_dist = dist
                closest_grib = (g_lat, g_lon)

        print(f"   Boundary[{idx:4d}]: ({b_lat:7.3f}°, {b_lon:8.3f}°)")
        print(f"   Closest GRIB:    ({closest_grib[0]:7.3f}°, {closest_grib[1]:8.3f}°)")
        print(f"   Distance: {min_dist:.6f}°")
        print()

    # Check if boundary approximately matches GRIB edges
    print(f"\n📊 Boundary vs GRIB Extent Comparison:")

    boundary_extent = {
        'lat_min': min(boundary_lats),
        'lat_max': max(boundary_lats),
        'lon_min': min(boundary_lons),
        'lon_max': max(boundary_lons)
    }

    grib_extent = {
        'lat_min': float(grib_lats.min()),
        'lat_max': float(grib_lats.max()),
        'lon_min': float(grib_lons_180.min()),
        'lon_max': float(grib_lons_180.max())
    }

    print(f"   Boundary: lat [{boundary_extent['lat_min']:.3f}, {boundary_extent['lat_max']:.3f}]")
    print(f"   GRIB:     lat [{grib_extent['lat_min']:.3f}, {grib_extent['lat_max']:.3f}]")
    print(f"   Difference: {abs(boundary_extent['lat_min'] - grib_extent['lat_min']):.6f}° (south), {abs(boundary_extent['lat_max'] - grib_extent['lat_max']):.6f}° (north)")
    print()
    print(f"   Boundary: lon [{boundary_extent['lon_min']:.3f}, {boundary_extent['lon_max']:.3f}]")
    print(f"   GRIB:     lon [{grib_extent['lon_min']:.3f}, {grib_extent['lon_max']:.3f}]")

    # Check if the boundary polygon is FROM the GRIB grid or somewhere else
    print(f"\n🤔 Is the boundary polygon FROM the GRIB grid edges?")

    # Check if boundary points are close to GRIB edge points
    matches = 0
    for b_lat, b_lon in zip(boundary_lats, boundary_lons):
        for g_lat, g_lon in grib_edge_points:
            dist = np.sqrt((b_lat - g_lat)**2 + (b_lon - g_lon)**2)
            if dist < 0.01:  # Within 0.01° (~1km)
                matches += 1
                break

    match_percent = (matches / len(boundary)) * 100
    print(f"   {matches} out of {len(boundary)} boundary points match GRIB edges ({match_percent:.1f}%)")

    if match_percent < 50:
        print(f"   ⚠️  WARNING: Boundary polygon does NOT appear to be from GRIB grid edges!")
        print(f"   The boundary polygon may be from a different source.")
    else:
        print(f"   ✓ Boundary polygon appears to be derived from GRIB grid edges")

    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    verify_boundary()
