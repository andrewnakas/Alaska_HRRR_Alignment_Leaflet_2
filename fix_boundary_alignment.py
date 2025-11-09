#!/usr/bin/env python3
"""
HRRR Alaska Boundary Alignment Fix

This script demonstrates the fix for the boundary polygon misalignment issue.
The boundary polygon is calculated from grid cell CENTERS but should use CORNERS.

Root Cause:
- GRIB2 grid cells have finite size (3km resolution)
- Current code uses cell CENTER coordinates
- Images extend to cell CORNERS (±dx/2, ±dy/2 from centers)
- This causes ~1.8km misalignment (half of 3km grid cell)

Solution:
- Offset the source transform by half a grid cell
- first_corner = first_center - (dx/2, dy/2)
- This aligns boundary with actual image pixel boundaries

Usage:
    python3 fix_boundary_alignment.py

This is a DEMONSTRATION script showing the conceptual fix.
The actual fix must be applied in the backend (Firebase Functions).
"""

import json
from typing import Dict, List, Tuple

def calculate_corrected_bounds(
    bounds: List[float],
    grid_resolution_km: float = 3.0
) -> List[float]:
    """
    Calculate corrected image bounds accounting for grid cell size.

    Args:
        bounds: [west, south, east, north] in degrees
        grid_resolution_km: Grid cell size in kilometers (default 3km for HRRR Alaska)

    Returns:
        Corrected bounds [west, south, east, north] in degrees
    """
    # Convert km to degrees (approximate)
    # At latitude ~60° (Alaska), 1° ≈ 55.8 km
    # More precisely: should vary by latitude, but for demonstration using average
    lat_deg_per_km = 1.0 / 111.0  # 1° latitude ≈ 111 km
    lon_deg_per_km = 1.0 / 55.8   # 1° longitude ≈ 55.8 km at 60°N (approximate)

    # Half grid cell offset
    half_cell_lat = (grid_resolution_km / 2.0) * lat_deg_per_km
    half_cell_lon = (grid_resolution_km / 2.0) * lon_deg_per_km

    west, south, east, north = bounds

    # Expand bounds by half grid cell in all directions
    corrected_bounds = [
        west - half_cell_lon,   # West edge moves west
        south - half_cell_lat,  # South edge moves south
        east + half_cell_lon,   # East edge moves east
        north + half_cell_lat   # North edge moves north
    ]

    return corrected_bounds


def expand_boundary_polygon(
    boundary: List[Dict[str, float]],
    grid_resolution_km: float = 3.0
) -> List[Dict[str, float]]:
    """
    Expand boundary polygon by half grid cell in all directions.

    This is a simplified demonstration. The actual fix should be applied
    in the backend by using corner coordinates in the source transform.

    Args:
        boundary: List of {lat, lon} points
        grid_resolution_km: Grid cell size in km

    Returns:
        Expanded boundary polygon
    """
    # Convert km to degrees
    lat_deg_per_km = 1.0 / 111.0
    lon_deg_per_km = 1.0 / 55.8  # Approximate for Alaska (60°N)

    half_cell_lat = (grid_resolution_km / 2.0) * lat_deg_per_km
    half_cell_lon = (grid_resolution_km / 2.0) * lon_deg_per_km

    # Find bounds of original polygon
    lats = [p['lat'] for p in boundary]
    lons = [p['lon'] for p in boundary]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Expand each point based on its position
    expanded = []
    for point in boundary:
        lat, lon = point['lat'], point['lon']

        # Determine which edge(s) this point is on
        on_south = abs(lat - min_lat) < 0.1
        on_north = abs(lat - max_lat) < 0.1
        on_west = abs(lon - min_lon) < 5.0  # Larger tolerance for lon
        on_east = abs(lon - max_lon) < 5.0

        # Offset based on edge position
        new_lat = lat
        new_lon = lon

        if on_south:
            new_lat -= half_cell_lat
        if on_north:
            new_lat += half_cell_lat
        if on_west:
            new_lon -= half_cell_lon
        if on_east:
            new_lon += half_cell_lon

        expanded.append({'lat': new_lat, 'lon': new_lon})

    return expanded


def analyze_alignment(data: Dict) -> None:
    """
    Analyze current alignment and show corrected values.

    Args:
        data: Alaska HRRR data dictionary
    """
    print("=" * 70)
    print("HRRR Alaska Boundary Alignment Analysis")
    print("=" * 70)

    # Extract data
    western_bounds = data['western']['bounds']
    eastern_bounds = data['eastern']['bounds']
    boundary = data['boundary_polygon']

    # Calculate boundary extent
    lats = [p['lat'] for p in boundary]
    lons = [p['lon'] for p in boundary]

    boundary_south = min(lats)
    boundary_north = max(lats)
    boundary_west = min(lons)
    boundary_east = max(lons)

    # Image bounds
    image_south = min(western_bounds[1], eastern_bounds[1])
    image_north = max(western_bounds[3], eastern_bounds[3])

    print("\n📊 CURRENT ALIGNMENT:")
    print(f"  Image South:    {image_south:.4f}°")
    print(f"  Boundary South: {boundary_south:.4f}°")
    print(f"  Error:          {abs(boundary_south - image_south):.4f}° = {abs(boundary_south - image_south) * 111:.2f} km")

    print(f"\n  Image North:    {image_north:.4f}°")
    print(f"  Boundary North: {boundary_north:.4f}°")
    print(f"  Error:          {abs(boundary_north - image_north):.4f}° = {abs(boundary_north - image_north) * 111:.2f} km")

    # Calculate expected values after fix
    grid_size_km = 3.0
    half_cell_deg = (grid_size_km / 2.0) / 111.0

    print(f"\n🔧 EXPECTED AFTER FIX (using corner coordinates):")
    print(f"  Grid resolution: {grid_size_km} km")
    print(f"  Half cell:       {half_cell_deg:.4f}° ≈ {grid_size_km/2:.1f} km")

    corrected_south = boundary_south - half_cell_deg
    corrected_north = boundary_north + half_cell_deg

    print(f"\n  Corrected Boundary South: {corrected_south:.4f}°")
    print(f"  Error from image:         {abs(corrected_south - image_south):.4f}° = {abs(corrected_south - image_south) * 111:.2f} km")

    print(f"\n  Corrected Boundary North: {corrected_north:.4f}°")
    print(f"  Error from image:         {abs(corrected_north - image_north):.4f}° = {abs(corrected_north - image_north) * 111:.2f} km")

    # Verdict
    current_error = max(abs(boundary_south - image_south), abs(boundary_north - image_north))
    expected_error = max(abs(corrected_south - image_south), abs(corrected_north - image_north))

    print(f"\n{'='*70}")
    if current_error > 0.01:
        print("⚠️  MISALIGNMENT DETECTED")
        print(f"   Current max error: {current_error:.4f}° = {current_error * 111:.2f} km")
    else:
        print("✅ ALIGNMENT OK")

    if expected_error < 0.01:
        print(f"✅ Fix will reduce error to: {expected_error:.4f}° = {expected_error * 111:.2f} km")

    print(f"{'='*70}\n")


def show_backend_fix() -> None:
    """Display the backend code fix."""
    print("🔧 BACKEND FIX (apply to /functions/main.py):\n")
    print("=" * 70)
    print("BEFORE (current code):")
    print("-" * 70)
    print("""
# Extract grid parameters from GRIB2
first_center_x = ...  # X coordinate of first grid cell CENTER
first_center_y = ...  # Y coordinate of first grid cell CENTER
dx = ...  # Grid cell width
dy = ...  # Grid cell height

# Create source transform
src_transform = from_origin(first_center_x, first_center_y, dx, -dy)
""")

    print("-" * 70)
    print("AFTER (fixed code):")
    print("-" * 70)
    print("""
# Extract grid parameters from GRIB2
first_center_x = ...  # X coordinate of first grid cell CENTER
first_center_y = ...  # Y coordinate of first grid cell CENTER
dx = ...  # Grid cell width
dy = ...  # Grid cell height

# ✨ FIX: Adjust to use CORNER coordinates instead of CENTERS
first_corner_x = first_center_x - dx / 2.0
first_corner_y = first_center_y - dy / 2.0

# Create source transform using corners
src_transform = from_origin(first_corner_x, first_corner_y, dx, -dy)
""")
    print("=" * 70)
    print("\n✅ This simple change aligns the boundary with actual image pixels.\n")


def main():
    """Main entry point."""
    # Load test data
    try:
        with open('test-data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: test-data.json not found")
        print("   Run this script from the repository root directory")
        return

    # Analyze current alignment
    analyze_alignment(data)

    # Show the fix
    show_backend_fix()

    print("📝 For detailed analysis, see: ALIGNMENT_ANALYSIS.md")
    print("🌐 Test harness: https://andrewnakas.github.io/Alaska_HRRR_Alignment_Leaflet_2/\n")


if __name__ == '__main__':
    main()
