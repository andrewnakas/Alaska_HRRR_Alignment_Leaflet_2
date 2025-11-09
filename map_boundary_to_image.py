#!/usr/bin/env python3
"""
Map Boundary Polygon to Image Space

This script maps the boundary polygon coordinates to image pixel space
to determine where the boundary SHOULD be in the image, then compares
that to where actual radar data exists.

This helps us determine the correct geographic bounds for the image.

Usage:
    python3 map_boundary_to_image.py
"""

import json
import numpy as np
from PIL import Image, ImageDraw

def map_boundary_to_pixels(boundary_polygon, image_bounds, image_shape):
    """
    Map boundary polygon lat/lon coordinates to image pixel coordinates.

    Args:
        boundary_polygon: List of {lat, lon} points
        image_bounds: [west, south, east, north] geographic bounds
        image_shape: (width, height) in pixels

    Returns:
        List of (x, y) pixel coordinates
    """
    west, south, east, north = image_bounds
    width, height = image_shape

    # Degrees per pixel
    deg_per_pixel_lon = (east - west) / width
    deg_per_pixel_lat = (north - south) / height

    pixel_coords = []

    for point in boundary_polygon:
        lat, lon = point['lat'], point['lon']

        # Convert to pixel coordinates
        # X: longitude (0 = west edge)
        x = (lon - west) / deg_per_pixel_lon

        # Y: latitude (0 = NORTH edge, increases downward)
        y = (north - lat) / deg_per_pixel_lat

        pixel_coords.append((x, y))

    return pixel_coords


def analyze_boundary_in_image(image_path, boundary_polygon, stated_bounds, label):
    """
    Analyze where the boundary polygon falls within the image.
    """
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

    # Load image
    img = Image.open(image_path)
    width, height = img.size
    img_array = np.array(img)

    print(f"Image: {width} × {height} pixels")
    print(f"Stated bounds: {stated_bounds}")

    # Map boundary to pixel coordinates
    pixel_coords = map_boundary_to_pixels(boundary_polygon, stated_bounds, (width, height))

    # Find extent of boundary polygon in pixel space
    xs = [coord[0] for coord in pixel_coords]
    ys = [coord[1] for coord in pixel_coords]

    boundary_pixel_extent = {
        'left': min(xs),
        'right': max(xs),
        'top': min(ys),
        'bottom': max(ys)
    }

    print(f"\n📍 Boundary Polygon in Image Space:")
    print(f"  X (longitude): {boundary_pixel_extent['left']:.1f} to {boundary_pixel_extent['right']:.1f}")
    print(f"  Y (latitude):  {boundary_pixel_extent['top']:.1f} to {boundary_pixel_extent['bottom']:.1f}")
    print(f"  Width:  {boundary_pixel_extent['right'] - boundary_pixel_extent['left']:.1f} pixels")
    print(f"  Height: {boundary_pixel_extent['bottom'] - boundary_pixel_extent['top']:.1f} pixels")

    # Find actual data extent in image
    if img.mode == 'RGBA':
        alpha = img_array[:, :, 3]
        data_mask = alpha > 0
    else:
        data_mask = np.any(img_array > 0, axis=2)

    rows_with_data = np.any(data_mask, axis=1)
    cols_with_data = np.any(data_mask, axis=0)

    if np.any(rows_with_data) and np.any(cols_with_data):
        row_indices = np.where(rows_with_data)[0]
        col_indices = np.where(cols_with_data)[0]

        actual_data_extent = {
            'left': col_indices[0],
            'right': col_indices[-1],
            'top': row_indices[0],
            'bottom': row_indices[-1]
        }

        print(f"\n📊 Actual Data in Image:")
        print(f"  X: {actual_data_extent['left']} to {actual_data_extent['right']}")
        print(f"  Y: {actual_data_extent['top']} to {actual_data_extent['bottom']}")
        print(f"  Width:  {actual_data_extent['right'] - actual_data_extent['left'] + 1} pixels")
        print(f"  Height: {actual_data_extent['bottom'] - actual_data_extent['top'] + 1} pixels")

        # Compare boundary polygon extent vs actual data extent
        print(f"\n🔍 Comparison:")
        print(f"  Boundary top:    {boundary_pixel_extent['top']:.1f}")
        print(f"  Data top:        {actual_data_extent['top']}")
        print(f"  Difference:      {actual_data_extent['top'] - boundary_pixel_extent['top']:.1f} pixels")

        print(f"\n  Boundary bottom: {boundary_pixel_extent['bottom']:.1f}")
        print(f"  Data bottom:     {actual_data_extent['bottom']}")
        print(f"  Difference:      {actual_data_extent['bottom'] - boundary_pixel_extent['bottom']:.1f} pixels")

        # Calculate where boundary SHOULD be geographically based on actual data
        west, south, east, north = stated_bounds
        deg_per_pixel_lon = (east - west) / width
        deg_per_pixel_lat = (north - south) / height

        # If boundary polygon is at pixels Y_top to Y_bottom,
        # what geographic bounds should the image have to align?

        # Current situation:
        # - Boundary polygon spans lat 41.621° to 77.085°
        # - We need to find what image bounds would make the boundary
        #   align with the actual data pixels

        boundary_lat_range = 77.085 - 41.621  # From your boundary polygon
        boundary_pixel_height = boundary_pixel_extent['bottom'] - boundary_pixel_extent['top']

        # Degrees per pixel based on boundary polygon span
        boundary_deg_per_pixel = boundary_lat_range / boundary_pixel_height

        print(f"\n🌍 Geographic Mapping:")
        print(f"  Boundary spans: {boundary_lat_range:.3f}° latitude")
        print(f"  Boundary spans: {boundary_pixel_height:.1f} pixels")
        print(f"  Boundary deg/pixel: {boundary_deg_per_pixel:.6f}°/pixel")
        print(f"  Image deg/pixel: {deg_per_pixel_lat:.6f}°/pixel")
        print(f"  Ratio: {boundary_deg_per_pixel / deg_per_pixel_lat:.4f}")

        # Calculate what the image bounds SHOULD be to align data with boundary
        # If actual data is at pixels top to bottom,
        # and boundary polygon spans 41.621° to 77.085°,
        # then we need to adjust the image bounds

        # The boundary polygon northern edge (77.085°) should be at pixel Y_top
        # The boundary polygon southern edge (41.621°) should be at pixel Y_bottom

        # So if data_top corresponds to 77.085° and data_bottom to 41.621°:
        correct_north_for_data = north - (actual_data_extent['top'] * deg_per_pixel_lat)
        correct_south_for_data = north - ((actual_data_extent['bottom'] + 1) * deg_per_pixel_lat)

        # But we want the boundary polygon edges to align with data edges
        # So we need to find bounds where boundary_top aligns with data_top

        # The boundary polygon's northern point (77.085°) should correspond to data_top
        # The boundary polygon's southern point (41.621°) should correspond to data_bottom

        # Working backwards from boundary polygon coordinates:
        # If pixel Y corresponds to latitude L, then:
        # L = north - Y * deg_per_pixel_lat
        #
        # We want:
        # data_top -> 77.085°
        # data_bottom -> 41.621°
        #
        # So: 77.085 = north - data_top * deg_per_pixel_lat
        # Therefore: north = 77.085 + data_top * deg_per_pixel_lat

        boundary_north = 77.085  # Northern extent of boundary polygon
        boundary_south = 41.621  # Southern extent of boundary polygon

        # Calculate image bounds that would make data pixels align with boundary
        aligned_north = boundary_north + (actual_data_extent['top'] * deg_per_pixel_lat)
        aligned_south = boundary_south - ((height - actual_data_extent['bottom'] - 1) * deg_per_pixel_lat)

        # Alternative calculation: use the boundary polygon pixel positions
        # to calculate what the image north/south should be

        # If boundary top is at pixel boundary_pixel_extent['top']
        # and that should correspond to 77.085°,
        # then the image north edge (pixel 0) should be at:
        image_north_for_alignment = boundary_north + (boundary_pixel_extent['top'] * deg_per_pixel_lat)

        # If boundary bottom is at pixel boundary_pixel_extent['bottom']
        # and that should correspond to 41.621°,
        # then the image south edge (pixel height) should be at:
        image_south_for_alignment = boundary_north - ((boundary_pixel_extent['bottom'] + 1) * deg_per_pixel_lat)

        print(f"\n✨ Calculated Aligned Bounds:")
        print(f"  To align data with boundary polygon:")
        print(f"  North: {image_north_for_alignment:.6f}°")
        print(f"  South: {image_south_for_alignment:.6f}°")
        print(f"  Range: {image_north_for_alignment - image_south_for_alignment:.6f}°")

        return {
            'boundary_pixel_extent': boundary_pixel_extent,
            'actual_data_extent': actual_data_extent,
            'aligned_bounds': {
                'west': west,
                'south': image_south_for_alignment,
                'east': east,
                'north': image_north_for_alignment
            }
        }

    return None


def visualize_boundary_on_image(image_path, boundary_polygon, stated_bounds, output_path):
    """Create visualization showing boundary polygon on image."""
    img = Image.open(image_path).convert('RGBA')
    width, height = img.size

    # Create overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Map boundary to pixels
    pixel_coords = map_boundary_to_pixels(boundary_polygon, stated_bounds, (width, height))

    # Draw boundary polygon
    if len(pixel_coords) > 1:
        draw.polygon(pixel_coords, outline=(255, 0, 0, 200), width=3)

    # Composite
    result = Image.alpha_composite(img, overlay)
    result.save(output_path)
    print(f"\n📸 Saved visualization to: {output_path}")


def main():
    """Main analysis."""
    print("="*70)
    print("Boundary Polygon to Image Space Mapping")
    print("="*70)

    # Load data
    with open('test-data.json', 'r') as f:
        data = json.load(f)

    boundary_polygon = data['boundary_polygon']

    print(f"\nBoundary polygon: {len(boundary_polygon)} points")
    print(f"  First point: lat={boundary_polygon[0]['lat']:.4f}, lon={boundary_polygon[0]['lon']:.4f}")
    print(f"  Last point:  lat={boundary_polygon[-1]['lat']:.4f}, lon={boundary_polygon[-1]['lon']:.4f}")

    # Find extent
    lats = [p['lat'] for p in boundary_polygon]
    lons = [p['lon'] for p in boundary_polygon]
    print(f"  Latitude range: {min(lats):.4f}° to {max(lats):.4f}° ({max(lats) - min(lats):.4f}°)")
    print(f"  Longitude range: {min(lons):.4f}° to {max(lons):.4f}°")

    # Analyze western image
    western_result = analyze_boundary_in_image(
        'images/alaska_hrrr_western.webp',
        boundary_polygon,
        data['western']['bounds'],
        'Western Image Analysis'
    )

    # Analyze eastern image
    eastern_result = analyze_boundary_in_image(
        'images/alaska_hrrr_eastern.webp',
        boundary_polygon,
        data['eastern']['bounds'],
        'Eastern Image Analysis'
    )

    # Create visualizations
    visualize_boundary_on_image(
        'images/alaska_hrrr_western.webp',
        boundary_polygon,
        data['western']['bounds'],
        'western_with_boundary.png'
    )

    visualize_boundary_on_image(
        'images/alaska_hrrr_eastern.webp',
        boundary_polygon,
        data['eastern']['bounds'],
        'eastern_with_boundary.png'
    )

    # Summary
    print(f"\n{'='*70}")
    print("RECOMMENDATION")
    print(f"{'='*70}")

    if western_result and eastern_result:
        aligned_bounds = western_result['aligned_bounds']
        print(f"\nUpdate image bounds to:")
        print(f"  Western: [{aligned_bounds['west']:.6f}, {aligned_bounds['south']:.6f}, {aligned_bounds['east']:.6f}, {aligned_bounds['north']:.6f}]")

        aligned_bounds = eastern_result['aligned_bounds']
        print(f"  Eastern: [{aligned_bounds['west']:.6f}, {aligned_bounds['south']:.6f}, {aligned_bounds['east']:.6f}, {aligned_bounds['north']:.6f}]")

        # Save results
        results = {
            'western': western_result,
            'eastern': eastern_result
        }

        with open('boundary_alignment_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📝 Results saved to: boundary_alignment_results.json")

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
