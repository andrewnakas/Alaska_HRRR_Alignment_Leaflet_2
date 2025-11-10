#!/usr/bin/env python3
"""
Automatically optimize HRRR Alaska image alignment - Version 3.

Optimize position AND scale to fit all pixels inside boundary.
"""

import json
import numpy as np
from PIL import Image
from scipy.optimize import differential_evolution
from shapely.geometry import Polygon, Point
from shapely.prepared import prep

print("=" * 70)
print("AUTOMATIC ALIGNMENT OPTIMIZATION V3")
print("Optimizing position + scale to fit ALL pixels inside boundary")
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

# Detect data pixels
print("\n🔍 Detecting radar data pixels...")
if img_array.shape[2] == 4:  # RGBA
    alpha = img_array[:, :, 3]
    data_mask = alpha > 10
else:
    data_mask = np.ones((img.height, img.width), dtype=bool)

# Sample every 25th pixel
sample_step = 25
data_pixels = []
for y in range(0, img.height, sample_step):
    for x in range(0, img.width, sample_step):
        if data_mask[y, x]:
            data_pixels.append((x, y))

print(f"✓ Using {len(data_pixels)} sample points")

# Initial parameters
initial_center_lon = -0.615000
initial_center_lat = 55.783000
initial_width = 360.0
initial_height = 36.812820


def pixel_to_latlon(x, y, center_lon, center_lat, width_scale, height_scale):
    """Convert pixel coordinates to lat/lon."""
    width = initial_width * width_scale
    height = initial_height * height_scale

    west = center_lon - width / 2
    east = center_lon + width / 2
    north = center_lat + height / 2
    south = center_lat - height / 2

    lon = west + (x / img.width) * width
    lat = north - (y / img.height) * height

    # Handle dateline wrapping
    if lon < -180:
        lon += 360
    elif lon > 180:
        lon -= 360

    return lon, lat


def evaluate_params(params):
    """
    Evaluate parameter quality.

    params = [center_lon, center_lat, width_scale, height_scale]
    """
    center_lon, center_lat, width_scale, height_scale = params

    # Count pixels outside
    outside_count = 0
    for x, y in data_pixels:
        lon, lat = pixel_to_latlon(x, y, center_lon, center_lat, width_scale, height_scale)
        point = Point(lon, lat)
        if not prepared_boundary.contains(point):
            outside_count += 1

    # Penalty for scaling away from 1.0 (prefer to stay close to original size)
    scale_penalty = abs(width_scale - 1.0) * 10 + abs(height_scale - 1.0) * 10

    return outside_count + scale_penalty


# Initial evaluation
initial_params = [initial_center_lon, initial_center_lat, 1.0, 1.0]
initial_score = evaluate_params(initial_params)
print(f"\n🎯 Initial score: {initial_score:.2f}")

print("\n⚙️  Running global optimization...")
print("   Optimizing: position + scale")
print("   Search range: ±5° position, 0.85x-1.15x scale")
print("   This may take 3-4 minutes...\n")

# Search bounds
search_bounds = [
    (initial_center_lon - 5, initial_center_lon + 5),  # center_lon
    (initial_center_lat - 5, initial_center_lat + 5),  # center_lat
    (0.85, 1.15),  # width_scale
    (0.85, 1.15)   # height_scale
]

# Run optimization
result = differential_evolution(
    evaluate_params,
    search_bounds,
    strategy='best1bin',
    maxiter=150,
    popsize=20,
    tol=0.01,
    atol=0.001,
    updating='deferred',
    workers=1,
    disp=True,
    polish=True
)

optimized_center_lon, optimized_center_lat, optimized_width_scale, optimized_height_scale = result.x
final_score = result.fun

# Calculate final bounds
final_width = initial_width * optimized_width_scale
final_height = initial_height * optimized_height_scale
optimized_west = optimized_center_lon - final_width / 2
optimized_east = optimized_center_lon + final_width / 2
optimized_south = optimized_center_lat - final_height / 2
optimized_north = optimized_center_lat + final_height / 2

# Count actual pixels outside
actual_outside = sum(1 for x, y in data_pixels
                     if not prepared_boundary.contains(
                         Point(*pixel_to_latlon(x, y, optimized_center_lon, optimized_center_lat,
                                                optimized_width_scale, optimized_height_scale))))

print("\n" + "=" * 70)
print("OPTIMIZATION COMPLETE")
print("=" * 70)

print(f"\n📊 Results:")
print(f"   Final score: {final_score:.2f}")
print(f"   Pixels outside: {actual_outside} / {len(data_pixels)}")

print(f"\n📍 Optimized position:")
print(f"   Center Lon: {optimized_center_lon:.6f}° (shift: {optimized_center_lon - initial_center_lon:+.6f}°)")
print(f"   Center Lat: {optimized_center_lat:.6f}° (shift: {optimized_center_lat - initial_center_lat:+.6f}°)")

print(f"\n📏 Optimized scale:")
print(f"   Width scale:  {optimized_width_scale:.6f}x ({(optimized_width_scale - 1.0) * 100:+.2f}%)")
print(f"   Height scale: {optimized_height_scale:.6f}x ({(optimized_height_scale - 1.0) * 100:+.2f}%)")

print(f"\n📐 Optimized bounds:")
print(f"   West:  {optimized_west:.6f}°")
print(f"   South: {optimized_south:.6f}°")
print(f"   East:  {optimized_east:.6f}°")
print(f"   North: {optimized_north:.6f}°")
print(f"   Width: {final_width:.6f}° (was {initial_width:.6f}°)")
print(f"   Height: {final_height:.6f}° (was {initial_height:.6f}°)")

if actual_outside == 0:
    print("\n✓✓✓ PERFECT! All sampled data pixels fit inside boundary!")
elif actual_outside < 50:
    print(f"\n✓ VERY GOOD! Only {actual_outside} pixels outside (likely edge artifacts)")
else:
    print(f"\n⚠ {actual_outside} pixels still outside")

# Export
output = {
    "optimized_bounds": [
        float(optimized_west),
        float(optimized_south),
        float(optimized_east),
        float(optimized_north)
    ],
    "adjustments": {
        "offsetX": float(optimized_center_lon - initial_center_lon),
        "offsetY": float(optimized_center_lat - initial_center_lat),
        "scaleX": float(optimized_width_scale),
        "scaleY": float(optimized_height_scale)
    },
    "pixels_outside": int(actual_outside),
    "total_pixels_sampled": int(len(data_pixels)),
    "success": bool(actual_outside == 0)
}

with open('OPTIMIZED_BOUNDS.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n💾 Saved to OPTIMIZED_BOUNDS.json")

print("\n📋 Copy these bounds:")
print(f"   [{optimized_west:.6f}, {optimized_south:.6f}, {optimized_east:.6f}, {optimized_north:.6f}]")

print("\n🎛️  Interactive tool adjustments:")
print(f"   Horizontal Offset: {optimized_center_lon - initial_center_lon:+.6f}°")
print(f"   Vertical Offset:   {optimized_center_lat - initial_center_lat:+.6f}°")
print(f"   Horizontal Scale:  {optimized_width_scale:.6f}x")
print(f"   Vertical Scale:    {optimized_height_scale:.6f}x")

print("\n" + "=" * 70)
