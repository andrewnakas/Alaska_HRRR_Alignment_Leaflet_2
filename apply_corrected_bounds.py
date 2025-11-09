#!/usr/bin/env python3
"""
Apply Corrected Image Bounds

This script updates test-data.json with the corrected geographic bounds
based on actual radar data extent within the images (excluding padding).

The analysis found that images have significant vertical padding:
- Top: 129 pixels (10.8%) - transparent padding
- Bottom: 23 pixels (1.9%) - transparent padding

This causes stated bounds to be off by:
- North: -3.82° (-423 km)
- South: +0.68° (+75 km)

Usage:
    python3 apply_corrected_bounds.py
"""

import json
import sys

def main():
    """Apply corrected bounds from image analysis."""
    print("="*70)
    print("Applying Corrected Image Bounds")
    print("="*70)

    # Load analysis results
    try:
        with open('image_analysis_results.json', 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print("\n❌ Error: image_analysis_results.json not found")
        print("   Run: python3 analyze_image_bounds.py first")
        return 1

    # Load test data
    try:
        with open('test-data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("\n❌ Error: test-data.json not found")
        return 1

    # Extract corrected bounds
    western_corrected = results['western']['corrected_bounds']
    eastern_corrected = results['eastern']['corrected_bounds']

    print("\n📊 Current bounds:")
    print(f"  Western: {data['western']['bounds']}")
    print(f"  Eastern: {data['eastern']['bounds']}")

    print("\n✨ Corrected bounds (based on actual pixel data):")
    print(f"  Western: {western_corrected}")
    print(f"  Eastern: {eastern_corrected}")

    print("\n🔧 Offsets:")
    western_offsets = results['western']['offsets']
    eastern_offsets = results['eastern']['offsets']

    print(f"  Western:")
    print(f"    North: {western_offsets['north']:+.4f}° ({western_offsets['north'] * 111:.1f} km)")
    print(f"    South: {western_offsets['south']:+.4f}° ({western_offsets['south'] * 111:.1f} km)")

    print(f"  Eastern:")
    print(f"    North: {eastern_offsets['north']:+.4f}° ({eastern_offsets['north'] * 111:.1f} km)")
    print(f"    South: {eastern_offsets['south']:+.4f}° ({eastern_offsets['south'] * 111:.1f} km)")

    # Ask for confirmation
    print("\n" + "="*70)
    response = input("Apply these corrections to test-data.json? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Cancelled - no changes made")
        return 0

    # Apply corrections
    data['western']['bounds'] = western_corrected
    data['eastern']['bounds'] = eastern_corrected

    # Save updated data
    with open('test-data.json', 'w') as f:
        json.dump(data, f, indent=2)

    print("\n✅ test-data.json updated with corrected bounds")
    print("\n📝 Next steps:")
    print("  1. Refresh the test harness in your browser")
    print("  2. Check alignment - boundary should now match image edges")
    print("  3. Run diagnostics to verify improvement")
    print("\n🌐 Test harness: https://andrewnakas.github.io/Alaska_HRRR_Alignment_Leaflet_2/")
    print("="*70 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
