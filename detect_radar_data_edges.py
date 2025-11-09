#!/usr/bin/env python3
"""
Advanced HRRR Radar Data Edge Detection

This tool finds the ACTUAL boundaries of radar reflectivity data,
not just non-transparent pixels. It looks for actual colored radar
data (blues, greens, yellows, reds) to determine precise edges.

Approach:
1. Load image and convert to different color spaces
2. Find pixels that represent actual radar data (not just transparent vs opaque)
3. Detect contours/edges of the radar data region
4. Calculate precise geographic bounds

Usage:
    python3 detect_radar_data_edges.py
"""

import json
import numpy as np
from PIL import Image
import sys

def analyze_radar_data_extent(image_path, stated_bounds, label="Image"):
    """
    Find the actual extent of radar data by analyzing pixel values.

    Args:
        image_path: Path to the image file
        stated_bounds: [west, south, east, north] geographic bounds
        label: Label for output

    Returns:
        Dictionary with precise data bounds
    """
    print(f"\n{'='*70}")
    print(f"Analyzing Radar Data Extent: {label}")
    print(f"{'='*70}")

    try:
        img = Image.open(image_path)
        img_array = np.array(img)
        height, width = img_array.shape[:2]

        print(f"Image: {width} × {height} pixels, mode: {img.mode}")

        # Strategy 1: Find pixels with actual color data
        # Radar data typically has RGB values, not just alpha
        if img.mode == 'RGBA':
            r, g, b, a = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2], img_array[:,:,3]

            # Pixels with alpha > 0 AND some color
            has_alpha = a > 0
            has_color = (r > 0) | (g > 0) | (b > 0)
            has_significant_color = (r > 10) | (g > 10) | (b > 10)  # Not just faint edges

            print(f"\nPixel classification:")
            print(f"  Has alpha > 0: {np.sum(has_alpha)} pixels")
            print(f"  Has any color: {np.sum(has_color)} pixels")
            print(f"  Has significant color: {np.sum(has_significant_color)} pixels")

            # Use significant color as the mask for actual data
            data_mask = has_alpha & has_significant_color

        elif img.mode == 'RGB':
            r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]

            # Find non-black/non-white pixels (actual radar colors)
            not_black = (r > 10) | (g > 10) | (b > 10)
            not_white = (r < 245) | (g < 245) | (b < 245)
            data_mask = not_black & not_white
        else:
            # Fallback for other modes
            data_mask = img_array > 10

        print(f"  Radar data pixels: {np.sum(data_mask)} ({np.sum(data_mask)/(width*height)*100:.1f}%)")

        # Find bounding box of actual radar data
        rows_with_data = np.any(data_mask, axis=1)
        cols_with_data = np.any(data_mask, axis=0)

        if not np.any(rows_with_data) or not np.any(cols_with_data):
            print("⚠️  WARNING: No radar data pixels found!")
            return None

        row_indices = np.where(rows_with_data)[0]
        col_indices = np.where(cols_with_data)[0]

        data_top = row_indices[0]
        data_bottom = row_indices[-1]
        data_left = col_indices[0]
        data_right = col_indices[-1]

        data_width = data_right - data_left + 1
        data_height = data_bottom - data_top + 1

        print(f"\n📊 Radar Data Bounding Box:")
        print(f"  Rows: [{data_top}:{data_bottom}] ({data_height} pixels)")
        print(f"  Cols: [{data_left}:{data_right}] ({data_width} pixels)")
        print(f"  Coverage: {data_width} × {data_height} = {data_width * data_height} pixels")

        # Calculate padding
        pad_top = data_top
        pad_bottom = height - data_bottom - 1
        pad_left = data_left
        pad_right = width - data_right - 1

        print(f"\n📏 Padding from radar data:")
        print(f"  Top:    {pad_top:4d} px ({pad_top/height*100:5.1f}%)")
        print(f"  Bottom: {pad_bottom:4d} px ({pad_bottom/height*100:5.1f}%)")
        print(f"  Left:   {pad_left:4d} px ({pad_left/width*100:5.1f}%)")
        print(f"  Right:  {pad_right:4d} px ({pad_right/width*100:5.1f}%)")

        # Calculate precise geographic bounds
        west, south, east, north = stated_bounds

        lon_range = east - west
        lat_range = north - south

        deg_per_pixel_lon = lon_range / width
        deg_per_pixel_lat = lat_range / height

        # Precise bounds for actual radar data
        # Note: In images, row 0 is north, increasing rows go south
        precise_west = west + (data_left * deg_per_pixel_lon)
        precise_east = west + ((data_right + 1) * deg_per_pixel_lon)
        precise_north = north - (data_top * deg_per_pixel_lat)
        precise_south = north - ((data_bottom + 1) * deg_per_pixel_lat)

        print(f"\n🌍 Geographic Bounds:")
        print(f"  Stated:  [{west:.6f}, {south:.6f}, {east:.6f}, {north:.6f}]")
        print(f"  Precise: [{precise_west:.6f}, {precise_south:.6f}, {precise_east:.6f}, {precise_north:.6f}]")

        # Calculate corrections
        corrections = {
            'west': precise_west - west,
            'east': precise_east - east,
            'south': precise_south - south,
            'north': precise_north - north
        }

        print(f"\n🔧 Corrections needed:")
        for direction, offset in corrections.items():
            km = abs(offset) * 111
            symbol = "✅" if abs(offset) < 0.001 else ("⚠️" if abs(offset) < 0.01 else "🔴")
            print(f"  {direction.capitalize():6s}: {offset:+.6f}° ({offset * 111:+7.2f} km) {symbol}")

        max_offset = max(abs(v) for v in corrections.values())
        print(f"\n  Max offset: {max_offset:.6f}° ({max_offset * 111:.2f} km)")

        # Additional analysis: sample some radar data pixels
        print(f"\n🎨 Sample radar data pixel values:")
        sample_points = [
            (data_top + 10, data_left + 10, "Top-left"),
            (data_top + 10, width // 2, "Top-center"),
            ((data_top + data_bottom) // 2, width // 2, "Center"),
            (data_bottom - 10, width // 2, "Bottom-center")
        ]

        for row, col, location in sample_points:
            if 0 <= row < height and 0 <= col < width:
                pixel = img_array[row, col]
                if img.mode == 'RGBA':
                    print(f"  {location:15s}: R={pixel[0]:3d} G={pixel[1]:3d} B={pixel[2]:3d} A={pixel[3]:3d}")
                else:
                    print(f"  {location:15s}: {pixel}")

        return {
            'stated_bounds': stated_bounds,
            'precise_bounds': [precise_west, precise_south, precise_east, precise_north],
            'pixel_data_bounds': {
                'top': int(data_top),
                'bottom': int(data_bottom),
                'left': int(data_left),
                'right': int(data_right),
                'width': int(data_width),
                'height': int(data_height)
            },
            'padding': {
                'top': int(pad_top),
                'bottom': int(pad_bottom),
                'left': int(pad_left),
                'right': int(pad_right)
            },
            'corrections': corrections,
            'max_offset_deg': float(max_offset),
            'max_offset_km': float(max_offset * 111),
            'data_coverage_percent': float(np.sum(data_mask) / (width * height) * 100)
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def visualize_data_extent(image_path, result, output_path):
    """Create a visualization showing where radar data is."""
    try:
        from PIL import ImageDraw, ImageFont

        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        bounds = result['pixel_data_bounds']
        top = bounds['top']
        bottom = bounds['bottom']
        left = bounds['left']
        right = bounds['right']

        # Draw rectangle around actual data
        draw.rectangle([left, top, right, bottom], outline='red', width=3)

        # Draw corner markers
        marker_size = 20
        for corner in [(left, top), (right, top), (right, bottom), (left, bottom)]:
            x, y = corner
            draw.line([x-marker_size, y, x+marker_size, y], fill='red', width=2)
            draw.line([x, y-marker_size, x, y+marker_size], fill='red', width=2)

        img.save(output_path)
        print(f"\n📸 Visualization saved to: {output_path}")

    except Exception as e:
        print(f"⚠️  Could not create visualization: {e}")


def main():
    """Main analysis function."""
    print("="*70)
    print("HRRR Radar Data Edge Detection")
    print("="*70)

    # Load test data
    try:
        with open('test-data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: test-data.json not found")
        return 1

    # Analyze both images
    western_result = analyze_radar_data_extent(
        'images/alaska_hrrr_western.webp',
        data['western']['bounds'],
        'Western Image'
    )

    eastern_result = analyze_radar_data_extent(
        'images/alaska_hrrr_eastern.webp',
        data['eastern']['bounds'],
        'Eastern Image'
    )

    # Create visualizations
    if western_result:
        visualize_data_extent(
            'images/alaska_hrrr_western.webp',
            western_result,
            'western_data_extent.png'
        )

    if eastern_result:
        visualize_data_extent(
            'images/alaska_hrrr_eastern.webp',
            eastern_result,
            'eastern_data_extent.png'
        )

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY & RECOMMENDATIONS")
    print(f"{'='*70}")

    if western_result and eastern_result:
        print(f"\nWestern Image:")
        print(f"  Precise bounds: {western_result['precise_bounds']}")
        print(f"  Max offset: {western_result['max_offset_deg']:.6f}° ({western_result['max_offset_km']:.2f} km)")
        print(f"  Data coverage: {western_result['data_coverage_percent']:.1f}%")

        print(f"\nEastern Image:")
        print(f"  Precise bounds: {eastern_result['precise_bounds']}")
        print(f"  Max offset: {eastern_result['max_offset_deg']:.6f}° ({eastern_result['max_offset_km']:.2f} km)")
        print(f"  Data coverage: {eastern_result['data_coverage_percent']:.1f}%")

        # Save results
        results = {
            'western': western_result,
            'eastern': eastern_result
        }

        with open('radar_data_extent_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📝 Results saved to: radar_data_extent_results.json")

        # Check if bounds need updating
        max_offset = max(western_result['max_offset_deg'], eastern_result['max_offset_deg'])

        if max_offset > 0.01:
            print(f"\n🔴 SIGNIFICANT OFFSET: {max_offset:.4f}° ({max_offset * 111:.1f} km)")
            print(f"   Update test-data.json with precise bounds")
        elif max_offset > 0.001:
            print(f"\n⚠️  Minor offset: {max_offset:.6f}° ({max_offset * 111:.2f} km)")
        else:
            print(f"\n✅ Bounds are precise!")

    print(f"\n{'='*70}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
