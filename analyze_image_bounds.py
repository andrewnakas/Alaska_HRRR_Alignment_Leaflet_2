#!/usr/bin/env python3
"""
HRRR Alaska Image Bounds Analysis

This script analyzes the actual radar data extent within the image files.
The problem: Image bounds may include transparent/empty pixels, but the
actual radar data might not fill the entire image.

This tool:
1. Loads the WebP images
2. Finds the bounding box of actual radar data (non-transparent pixels)
3. Calculates the percentage of image used
4. Determines corrected geographic bounds for the actual data
5. Compares to the stated bounds to find misalignment

Usage:
    python3 analyze_image_bounds.py
"""

import json
import numpy as np
from PIL import Image
import sys

def analyze_image_data_bounds(image_path, stated_bounds, label="Image"):
    """
    Analyze where actual radar data exists within the image.

    Args:
        image_path: Path to the image file
        stated_bounds: [west, south, east, north] stated geographic bounds
        label: Label for output

    Returns:
        Dictionary with analysis results
    """
    print(f"\n{'='*70}")
    print(f"Analyzing: {label}")
    print(f"{'='*70}")

    try:
        img = Image.open(image_path)
        print(f"Image size: {img.size[0]} x {img.size[1]} pixels")
        print(f"Image mode: {img.mode}")

        # Convert to numpy array
        img_array = np.array(img)
        height, width = img_array.shape[:2]

        print(f"Array shape: {img_array.shape}")

        # Find non-transparent/non-zero pixels
        # Different strategies based on image mode
        if img.mode == 'RGBA':
            # Check alpha channel
            alpha = img_array[:, :, 3]
            mask = alpha > 0
            print(f"Mode: RGBA - using alpha channel")
        elif img.mode == 'RGB':
            # Check if any channel has data
            mask = np.any(img_array > 0, axis=2)
            print(f"Mode: RGB - checking for non-zero pixels")
        else:
            # Grayscale or other
            mask = img_array > 0
            print(f"Mode: {img.mode} - checking for non-zero values")

        # Find bounding box of data
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            print("⚠️  WARNING: No data pixels found in image!")
            return None

        row_indices = np.where(rows)[0]
        col_indices = np.where(cols)[0]

        # Pixel bounds of actual data
        data_top = row_indices[0]
        data_bottom = row_indices[-1]
        data_left = col_indices[0]
        data_right = col_indices[-1]

        data_width = data_right - data_left + 1
        data_height = data_bottom - data_top + 1

        print(f"\n📊 Pixel Analysis:")
        print(f"  Full image:    {width} x {height} pixels")
        print(f"  Data bounds:   rows [{data_top}:{data_bottom}], cols [{data_left}:{data_right}]")
        print(f"  Data size:     {data_width} x {data_height} pixels")
        print(f"  Data coverage: {(data_width * data_height) / (width * height) * 100:.1f}%")

        # Calculate padding
        padding_top = data_top
        padding_bottom = height - data_bottom - 1
        padding_left = data_left
        padding_right = width - data_right - 1

        print(f"\n📏 Padding:")
        print(f"  Top:    {padding_top} pixels ({padding_top/height*100:.1f}%)")
        print(f"  Bottom: {padding_bottom} pixels ({padding_bottom/height*100:.1f}%)")
        print(f"  Left:   {padding_left} pixels ({padding_left/width*100:.1f}%)")
        print(f"  Right:  {padding_right} pixels ({padding_right/width*100:.1f}%)")

        # Calculate corrected geographic bounds
        # stated_bounds = [west, south, east, north]
        west, south, east, north = stated_bounds

        # Calculate degrees per pixel
        lon_range = east - west
        lat_range = north - south

        deg_per_pixel_lon = lon_range / width
        deg_per_pixel_lat = lat_range / height

        # Corrected bounds based on actual data location
        # Note: In images, row 0 is at the top (north), increasing downward (south)
        corrected_west = west + (data_left * deg_per_pixel_lon)
        corrected_east = west + ((data_right + 1) * deg_per_pixel_lon)
        corrected_north = north - (data_top * deg_per_pixel_lat)
        corrected_south = north - ((data_bottom + 1) * deg_per_pixel_lat)

        print(f"\n🌍 Geographic Bounds:")
        print(f"  Stated bounds:    [{west:.4f}, {south:.4f}, {east:.4f}, {north:.4f}]")
        print(f"  Corrected bounds: [{corrected_west:.4f}, {corrected_south:.4f}, {corrected_east:.4f}, {corrected_north:.4f}]")

        # Calculate offsets
        west_offset = corrected_west - west
        east_offset = corrected_east - east
        south_offset = corrected_south - south
        north_offset = corrected_north - north

        print(f"\n🔧 Corrections needed:")
        print(f"  West:  {west_offset:+.6f}° ({west_offset * 111:.2f} km)")
        print(f"  East:  {east_offset:+.6f}° ({east_offset * 111:.2f} km)")
        print(f"  South: {south_offset:+.6f}° ({south_offset * 111:.2f} km)")
        print(f"  North: {north_offset:+.6f}° ({north_offset * 111:.2f} km)")

        max_offset = max(abs(west_offset), abs(east_offset), abs(south_offset), abs(north_offset))

        if max_offset > 0.01:
            print(f"\n⚠️  SIGNIFICANT OFFSET DETECTED: {max_offset:.4f}° ({max_offset * 111:.2f} km)")
        elif max_offset > 0.001:
            print(f"\n✓ Minor offset: {max_offset:.4f}° ({max_offset * 111:.2f} km)")
        else:
            print(f"\n✅ Bounds are well-aligned: {max_offset:.6f}° ({max_offset * 111:.2f} km)")

        return {
            'stated_bounds': stated_bounds,
            'corrected_bounds': [corrected_west, corrected_south, corrected_east, corrected_north],
            'pixel_data_bounds': {
                'top': int(data_top),
                'bottom': int(data_bottom),
                'left': int(data_left),
                'right': int(data_right)
            },
            'pixel_padding': {
                'top': int(padding_top),
                'bottom': int(padding_bottom),
                'left': int(padding_left),
                'right': int(padding_right)
            },
            'offsets': {
                'west': float(west_offset),
                'east': float(east_offset),
                'south': float(south_offset),
                'north': float(north_offset)
            },
            'max_offset_deg': float(max_offset),
            'max_offset_km': float(max_offset * 111)
        }

    except Exception as e:
        print(f"❌ Error analyzing image: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main analysis function."""
    print("="*70)
    print("HRRR Alaska Image Bounds Analysis")
    print("="*70)

    # Load test data
    try:
        with open('test-data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: test-data.json not found")
        print("   Run this script from the repository root directory")
        return 1

    # Analyze western image
    western_result = analyze_image_data_bounds(
        'images/alaska_hrrr_western.webp',
        data['western']['bounds'],
        'Western Hemisphere Image'
    )

    # Analyze eastern image
    eastern_result = analyze_image_data_bounds(
        'images/alaska_hrrr_eastern.webp',
        data['eastern']['bounds'],
        'Eastern Hemisphere Image'
    )

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    if western_result and eastern_result:
        print(f"\nWestern Image:")
        print(f"  Max offset: {western_result['max_offset_deg']:.4f}° ({western_result['max_offset_km']:.2f} km)")
        print(f"  Corrected bounds: {western_result['corrected_bounds']}")

        print(f"\nEastern Image:")
        print(f"  Max offset: {eastern_result['max_offset_deg']:.4f}° ({eastern_result['max_offset_km']:.2f} km)")
        print(f"  Corrected bounds: {eastern_result['corrected_bounds']}")

        # Check if we should update test-data.json
        max_total_offset = max(western_result['max_offset_deg'], eastern_result['max_offset_deg'])

        if max_total_offset > 0.01:
            print(f"\n⚠️  RECOMMENDATION:")
            print(f"  Images have significant padding/offset ({max_total_offset:.4f}°)")
            print(f"  Should update test-data.json with corrected bounds")
            print(f"\n  Run: python3 apply_corrected_bounds.py")
        elif max_total_offset > 0.001:
            print(f"\n✓ Minor offset detected ({max_total_offset:.4f}°)")
            print(f"  May want to apply correction for perfect alignment")
        else:
            print(f"\n✅ Image bounds are well-aligned")
            print(f"  The 1.8km misalignment is from grid center vs corner issue")
            print(f"  See ALIGNMENT_ANALYSIS.md for the backend fix")

        # Save results
        results = {
            'western': western_result,
            'eastern': eastern_result
        }

        with open('image_analysis_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📝 Results saved to: image_analysis_results.json")

    else:
        print("\n❌ Analysis failed for one or more images")
        return 1

    print(f"\n{'='*70}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
