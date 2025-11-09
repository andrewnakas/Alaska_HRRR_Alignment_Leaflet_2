#!/usr/bin/env python3
"""
Compare Western and Eastern Images

Are they different images or the same image duplicated?
"""

import numpy as np
from PIL import Image

def compare_images():
    print("="*70)
    print("COMPARING WESTERN AND EASTERN IMAGES")
    print("="*70)

    # Load both images
    img_west = Image.open('images/alaska_hrrr_western.webp')
    img_east = Image.open('images/alaska_hrrr_eastern.webp')

    arr_west = np.array(img_west)
    arr_east = np.array(img_east)

    print(f"\nWestern image: {arr_west.shape}")
    print(f"Eastern image: {arr_east.shape}")

    # Check if they're identical
    if arr_west.shape != arr_east.shape:
        print("\n❌ Images have different dimensions!")
        print("   They are definitely different images.")
    else:
        # Compare pixel by pixel
        differences = np.sum(arr_west != arr_east)
        total_pixels = arr_west.size

        if differences == 0:
            print("\n✅ Images are IDENTICAL (exact copy)")
        else:
            percent_diff = (differences / total_pixels) * 100
            print(f"\n⚠️  Images are DIFFERENT")
            print(f"   Different pixels: {differences:,} out of {total_pixels:,} ({percent_diff:.2f}%)")

    # Sample some pixels to see the difference
    height, width = arr_west.shape[:2]

    print(f"\n🔍 Sampling pixels at different locations:")

    # Sample corners
    locations = [
        (0, 0, "Top-left"),
        (0, width-1, "Top-right"),
        (height-1, 0, "Bottom-left"),
        (height-1, width-1, "Bottom-right"),
        (height//2, width//2, "Center"),
        (500, 3000, "Sample 1"),
        (500, 9000, "Sample 2")
    ]

    for row, col, label in locations:
        west_pixel = arr_west[row, col]
        east_pixel = arr_east[row, col]
        match = "✓" if np.array_equal(west_pixel, east_pixel) else "✗"
        print(f"   {label:15s} ({row:4d}, {col:5d}): {match} West={west_pixel} East={east_pixel}")

    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    compare_images()
