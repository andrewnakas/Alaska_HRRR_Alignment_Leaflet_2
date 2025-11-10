#!/usr/bin/env python3
"""
Automatically optimize HRRR Alaska image alignment.

Goal: Find bounds where all radar pixels fit inside the boundary polygon
while maximizing the number of pixels touching the boundary edges.
"""

import json
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from shapely.geometry import Polygon, Point
from shapely.prepared import prep
import sys

print("=" * 70)
print("AUTOMATIC ALIGNMENT OPTIMIZATION")
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
    data_mask = alpha > 10  # Pixels with alpha > 10 are data
else:
    # Assume all pixels are data if no alpha channel
    data_mask = np.ones((img.height, img.width), dtype=bool)

# Sample data pixels for faster optimization (every 10th pixel)
sample_step = 10
data_pixels = []
for y in range(0, img.height, sample_step):
    for x in range(0, img.width, sample_step):
        if data_mask[y, x]:
            data_pixels.append((x, y))

print(f"✓ Found {np.sum(data_mask)} data pixels")
print(f"✓ Using {len(data_pixels)} sample points for optimization")

# Edge pixels (for border contact scoring)
edge_pixels = []
for y in range(0, img.height, sample_step):
    for x in range(0, img.width, sample_step):
        if data_mask[y, x]:
            # Check if pixel is on the edge of data
            neighbors = [
                (x-1, y), (x+1, y), (x, y-1), (x, y+1)
            ]
            is_edge = False
            for nx, ny in neighbors:
                if 0 <= nx < img.width and 0 <= ny < img.height:
                    if not data_mask[ny, nx]:
                        is_edge = True
                        break
            if is_edge:
                edge_pixels.append((x, y))

print(f"✓ Identified {len(edge_pixels)} edge pixels")


def pixel_to_latlon(x, y, bounds):
    """Convert pixel coordinates to lat/lon given bounds."""
    west, south, east, north = bounds

    lon = west + (x / img.width) * (east - west)
    lat = north - (y / img.height) * (north - south)

    return lon, lat


def evaluate_bounds(params):
    """
    Evaluate bounds quality.

    params = [west, south, east, north]

    Returns a score where:
    - Negative infinity if any data pixel is outside boundary
    - Otherwise, negative count of edge pixels near boundary (to maximize)
    """
    west, south, east, north = params
    bounds = (west, south, east, north)

    # Check if all data pixels are inside boundary
    outside_count = 0
    for x, y in data_pixels:
        lon, lat = pixel_to_latlon(x, y, bounds)
        point = Point(lon, lat)
        if not prepared_boundary.contains(point):
            outside_count += 1

    # If any pixels are outside, heavily penalize
    if outside_count > 0:
        return 1e6 + outside_count * 1000

    # Count edge pixels near boundary (within 0.1 degrees)
    near_boundary_count = 0
    for x, y in edge_pixels:
        lon, lat = pixel_to_latlon(x, y, bounds)
        point = Point(lon, lat)
        distance = point.distance(boundary_polygon.boundary)
        if distance < 0.1:  # Within 0.1 degrees of boundary
            near_boundary_count += 1

    # Return negative (we want to maximize near_boundary_count)
    # Also add small penalty for image size to prefer tighter fits
    width = east - west
    height = north - south
    size_penalty = (width + height) * 0.001

    return -near_boundary_count + size_penalty


# Starting bounds (from user adjustment)
initial_bounds = np.array([
    -180.615000,  # west
    37.376590,    # south
    179.385000,   # east
    74.189410     # north
])

print(f"\n🎯 Initial bounds: {initial_bounds}")
print(f"   Width: {initial_bounds[2] - initial_bounds[0]:.6f}°")
print(f"   Height: {initial_bounds[3] - initial_bounds[1]:.6f}°")

# Evaluate initial bounds
initial_score = evaluate_bounds(initial_bounds)
print(f"   Initial score: {initial_score:.2f}")

print("\n⚙️  Running optimization...")
print("   Method: Nelder-Mead (simplex)")
print("   This may take 1-2 minutes...\n")

# Optimization bounds (reasonable ranges)
bounds_constraints = [
    (-185, -175),  # west
    (35, 42),      # south
    (175, 185),    # east
    (70, 78)       # north
]

# Run optimization
result = minimize(
    evaluate_bounds,
    initial_bounds,
    method='Nelder-Mead',
    options={
        'maxiter': 1000,
        'xatol': 0.0001,  # 0.0001 degree tolerance (~11m)
        'fatol': 1.0,
        'disp': True
    }
)

optimized_bounds = result.x
final_score = result.fun

print("\n" + "=" * 70)
print("OPTIMIZATION COMPLETE")
print("=" * 70)

print(f"\n📊 Results:")
print(f"   Status: {result.message}")
print(f"   Iterations: {result.nit}")
print(f"   Final score: {final_score:.2f}")

print(f"\n📐 Optimized bounds:")
print(f"   West:  {optimized_bounds[0]:.6f}° (change: {optimized_bounds[0] - initial_bounds[0]:+.6f}°)")
print(f"   South: {optimized_bounds[1]:.6f}° (change: {optimized_bounds[1] - initial_bounds[1]:+.6f}°)")
print(f"   East:  {optimized_bounds[2]:.6f}° (change: {optimized_bounds[2] - initial_bounds[2]:+.6f}°)")
print(f"   North: {optimized_bounds[3]:.6f}° (change: {optimized_bounds[3] - initial_bounds[3]:+.6f}°)")
print(f"   Width: {optimized_bounds[2] - optimized_bounds[0]:.6f}°")
print(f"   Height: {optimized_bounds[3] - optimized_bounds[1]:.6f}°")

# Verify all pixels are inside
print("\n✓ Verifying all data pixels are inside boundary...")
outside_count = 0
for x, y in data_pixels:
    lon, lat = pixel_to_latlon(x, y, optimized_bounds)
    point = Point(lon, lat)
    if not prepared_boundary.contains(point):
        outside_count += 1

if outside_count == 0:
    print("   ✓ All sampled data pixels are inside boundary!")
else:
    print(f"   ⚠ Warning: {outside_count} pixels still outside")

# Export results
output = {
    "optimized_bounds": [float(x) for x in optimized_bounds],
    "initial_bounds": [float(x) for x in initial_bounds],
    "changes": {
        "west": float(optimized_bounds[0] - initial_bounds[0]),
        "south": float(optimized_bounds[1] - initial_bounds[1]),
        "east": float(optimized_bounds[2] - initial_bounds[2]),
        "north": float(optimized_bounds[3] - initial_bounds[3])
    },
    "score": float(final_score),
    "iterations": int(result.nit),
    "success": bool(result.success)
}

with open('OPTIMIZED_BOUNDS.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n💾 Saved results to OPTIMIZED_BOUNDS.json")

# Format for easy copying
bounds_array = f"[{optimized_bounds[0]:.6f}, {optimized_bounds[1]:.6f}, {optimized_bounds[2]:.6f}, {optimized_bounds[3]:.6f}]"
print("\n📋 Copy these bounds:")
print(f"   {bounds_array}")

print("\n" + "=" * 70)
