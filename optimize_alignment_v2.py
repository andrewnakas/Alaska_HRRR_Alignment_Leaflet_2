#!/usr/bin/env python3
"""
Automatically optimize HRRR Alaska image alignment - Version 2.

Better approach: Keep image size constant, optimize position only.
"""

import json
import numpy as np
from PIL import Image
from scipy.optimize import differential_evolution
from shapely.geometry import Polygon, Point
from shapely.prepared import prep

print("=" * 70)
print("AUTOMATIC ALIGNMENT OPTIMIZATION V2")
print("=" * 70)

# Load test data
print("\n📂 Loading data...")
with open('test-data.json', 'r') as f:
    data = json.load(f)

boundary_coords = [(p['lon'], p['lat']) for p in data['boundary_polygon']]
boundary_polygon = Polygon(boundary_coords)
prepared_boundary = prep(boundary_polygon)

print(f"✓ Loaded boundary polygon with {len(boundary_coords)} points")

# Load image
print("\n🖼️  Loading image...")
img = Image.open('images/alaska_hrrr_western.webp')
img_array = np.array(img)
print(f"✓ Image size: {img.width} x {img.height}")

# Detect data pixels (non-transparent)
print("\n🔍 Detecting radar data pixels...")
if img_array.shape[2] == 4:  # RGBA
    alpha = img_array[:, :, 3]
    data_mask = alpha > 10
else:
    data_mask = np.ones((img.height, img.width), dtype=bool)

# Sample data pixels (every 20th pixel for speed)
sample_step = 20
data_pixels = []
for y in range(0, img.height, sample_step):
    for x in range(0, img.width, sample_step):
        if data_mask[y, x]:
            data_pixels.append((x, y))

print(f"✓ Found {np.sum(data_mask)} data pixels")
print(f"✓ Using {len(data_pixels)} sample points for optimization")

# Initial bounds (from user adjustment)
initial_west = -180.615000
initial_south = 37.376590
initial_east = 179.385000
initial_north = 74.189410

# Calculate fixed width and height
fixed_width = initial_east - initial_west  # 360.0
fixed_height = initial_north - initial_south  # 36.81282

print(f"\n📏 Fixed dimensions:")
print(f"   Width: {fixed_width:.6f}°")
print(f"   Height: {fixed_height:.6f}°")


def pixel_to_latlon(x, y, center_lon, center_lat):
    """Convert pixel coordinates to lat/lon given center position."""
    # Calculate bounds from center
    west = center_lon - fixed_width / 2
    east = center_lon + fixed_width / 2
    north = center_lat + fixed_height / 2
    south = center_lat - fixed_height / 2

    lon = west + (x / img.width) * fixed_width
    lat = north - (y / img.height) * fixed_height

    return lon, lat


def evaluate_position(params):
    """
    Evaluate position quality.

    params = [center_lon, center_lat]

    Returns count of data pixels OUTSIDE boundary (to minimize).
    """
    center_lon, center_lat = params

    # Count pixels outside boundary
    outside_count = 0
    for x, y in data_pixels:
        lon, lat = pixel_to_latlon(x, y, center_lon, center_lat)

        # Handle dateline wrapping
        if lon < -180:
            lon += 360
        elif lon > 180:
            lon -= 360

        point = Point(lon, lat)
        if not prepared_boundary.contains(point):
            outside_count += 1

    return outside_count


# Initial center position
initial_center_lon = (initial_west + initial_east) / 2  # -0.615
initial_center_lat = (initial_south + initial_north) / 2  # 55.782995

print(f"\n🎯 Initial center: ({initial_center_lon:.6f}, {initial_center_lat:.6f})")

# Evaluate initial position
initial_outside = evaluate_position([initial_center_lon, initial_center_lat])
print(f"   Pixels outside boundary: {initial_outside}")

print("\n⚙️  Running optimization...")
print("   Method: Differential Evolution (global optimization)")
print("   Searching for best position within ±5° of initial...")
print("   This may take 2-3 minutes...\n")

# Search bounds (±5 degrees from initial position)
search_bounds = [
    (initial_center_lon - 5, initial_center_lon + 5),  # center_lon
    (initial_center_lat - 5, initial_center_lat + 5)   # center_lat
]

# Run global optimization
result = differential_evolution(
    evaluate_position,
    search_bounds,
    strategy='best1bin',
    maxiter=100,
    popsize=15,
    tol=0.001,
    atol=0.0001,
    updating='deferred',
    workers=1,
    disp=True,
    polish=True
)

optimized_center_lon, optimized_center_lat = result.x
final_outside = result.fun

# Calculate final bounds
optimized_west = optimized_center_lon - fixed_width / 2
optimized_east = optimized_center_lon + fixed_width / 2
optimized_south = optimized_center_lat - fixed_height / 2
optimized_north = optimized_center_lat + fixed_height / 2

print("\n" + "=" * 70)
print("OPTIMIZATION COMPLETE")
print("=" * 70)

print(f"\n📊 Results:")
print(f"   Status: {result.message}")
print(f"   Iterations: {result.nit}")
print(f"   Pixels outside: {int(final_outside)} (initial: {initial_outside})")

print(f"\n📍 Optimized center:")
print(f"   Longitude: {optimized_center_lon:.6f}° (shift: {optimized_center_lon - initial_center_lon:+.6f}°)")
print(f"   Latitude:  {optimized_center_lat:.6f}° (shift: {optimized_center_lat - initial_center_lat:+.6f}°)")

print(f"\n📐 Optimized bounds:")
print(f"   West:  {optimized_west:.6f}° (change: {optimized_west - initial_west:+.6f}°)")
print(f"   South: {optimized_south:.6f}° (change: {optimized_south - initial_south:+.6f}°)")
print(f"   East:  {optimized_east:.6f}° (change: {optimized_east - initial_east:+.6f}°)")
print(f"   North: {optimized_north:.6f}° (change: {optimized_north - initial_north:+.6f}°)")

# Verify
if final_outside == 0:
    print("\n✓✓✓ SUCCESS! All sampled data pixels are inside boundary!")
else:
    print(f"\n⚠ {int(final_outside)} pixels still outside (out of {len(data_pixels)} sampled)")
    print("   Try running again with smaller sample_step for better accuracy")

# Export results
output = {
    "optimized_bounds": [
        float(optimized_west),
        float(optimized_south),
        float(optimized_east),
        float(optimized_north)
    ],
    "initial_bounds": [
        float(initial_west),
        float(initial_south),
        float(initial_east),
        float(initial_north)
    ],
    "center": {
        "longitude": float(optimized_center_lon),
        "latitude": float(optimized_center_lat)
    },
    "shifts": {
        "longitude": float(optimized_center_lon - initial_center_lon),
        "latitude": float(optimized_center_lat - initial_center_lat)
    },
    "pixels_outside": int(final_outside),
    "success": bool(final_outside == 0)
}

with open('OPTIMIZED_BOUNDS.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n💾 Saved results to OPTIMIZED_BOUNDS.json")

# Format for easy copying
bounds_array = f"[{optimized_west:.6f}, {optimized_south:.6f}, {optimized_east:.6f}, {optimized_north:.6f}]"
print("\n📋 Copy these bounds:")
print(f"   {bounds_array}")

# Show what to adjust in interactive tool
print("\n🎛️  Or adjust in interactive tool:")
print(f"   Horizontal Offset: {optimized_center_lon - initial_center_lon:+.6f}°")
print(f"   Vertical Offset:   {optimized_center_lat - initial_center_lat:+.6f}°")

print("\n" + "=" * 70)
