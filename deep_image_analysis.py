#!/usr/bin/env python3
"""
Deep Image Analysis - Understanding HRRR Image Content

This script performs a comprehensive analysis of the HRRR images to understand:
- What percentage of pixels have different alpha values
- What colors are present
- Where the actual reflectivity data is

Usage:
    python3 deep_image_analysis.py
"""

import numpy as np
from PIL import Image
import json

def deep_analyze_image(image_path, label):
    """Comprehensive image analysis."""
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

    img = Image.open(image_path)
    img_array = np.array(img)
    height, width = img_array.shape[:2]

    print(f"Image: {width} × {height} pixels")
    print(f"Mode: {img.mode}")

    if img.mode == 'RGBA':
        r, g, b, a = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2], img_array[:,:,3]

        # Alpha channel analysis
        print(f"\n📊 Alpha Channel Distribution:")
        unique_alpha, counts = np.unique(a, return_counts=True)
        total_pixels = width * height

        for alpha_val, count in zip(unique_alpha[:10], counts[:10]):  # Show first 10
            pct = count / total_pixels * 100
            print(f"  Alpha={alpha_val:3d}: {count:8d} pixels ({pct:5.2f}%)")

        if len(unique_alpha) > 10:
            print(f"  ... {len(unique_alpha) - 10} more alpha values")

        # Different thresholds
        alpha_0 = np.sum(a == 0)
        alpha_gt_0 = np.sum(a > 0)
        alpha_gt_128 = np.sum(a > 128)
        alpha_255 = np.sum(a == 255)

        print(f"\n  Alpha =   0: {alpha_0:8d} ({alpha_0/total_pixels*100:5.2f}%) - fully transparent")
        print(f"  Alpha >   0: {alpha_gt_0:8d} ({alpha_gt_0/total_pixels*100:5.2f}%) - any opacity")
        print(f"  Alpha > 128: {alpha_gt_128:8d} ({alpha_gt_128/total_pixels*100:5.2f}%) - mostly opaque")
        print(f"  Alpha = 255: {alpha_255:8d} ({alpha_255/total_pixels*100:5.2f}%) - fully opaque")

        # RGB analysis for pixels with alpha > 0
        mask_visible = a > 0
        print(f"\n🎨 RGB Analysis (for alpha > 0 pixels):")

        if np.any(mask_visible):
            r_visible = r[mask_visible]
            g_visible = g[mask_visible]
            b_visible = b[mask_visible]

            print(f"  R: min={r_visible.min():3d}, max={r_visible.max():3d}, mean={r_visible.mean():6.2f}")
            print(f"  G: min={g_visible.min():3d}, max={g_visible.max():3d}, mean={g_visible.mean():6.2f}")
            print(f"  B: min={b_visible.min():3d}, max={b_visible.max():3d}, mean={b_visible.mean():6.2f}")

            # Find actual colored pixels (not just faint edges)
            has_real_color = (r_visible > 20) | (g_visible > 20) | (b_visible > 20)
            real_color_count = np.sum(has_real_color)
            print(f"\n  Pixels with R/G/B > 20: {real_color_count:8d} ({real_color_count/total_pixels*100:5.2f}%)")

        # Spatial analysis - where is the data?
        print(f"\n📍 Spatial Distribution:")
        rows_with_alpha = np.any(a > 0, axis=1)
        cols_with_alpha = np.any(a > 0, axis=0)

        row_indices = np.where(rows_with_alpha)[0]
        col_indices = np.where(cols_with_alpha)[0]

        if len(row_indices) > 0 and len(col_indices) > 0:
            data_top = row_indices[0]
            data_bottom = row_indices[-1]
            data_left = col_indices[0]
            data_right = col_indices[-1]

            print(f"  Data extent:")
            print(f"    Rows: {data_top:4d} to {data_bottom:4d} ({data_bottom - data_top + 1:4d} pixels)")
            print(f"    Cols: {data_left:4d} to {data_right:4d} ({data_right - data_left + 1:4d} pixels)")

            # Sample some rows to see distribution
            print(f"\n  Row-by-row analysis (sample):")
            sample_rows = [data_top, data_top + 100, (data_top + data_bottom)//2, data_bottom - 100, data_bottom]
            for row in sample_rows:
                if 0 <= row < height:
                    row_data = a[row, :]
                    count_visible = np.sum(row_data > 0)
                    count_opaque = np.sum(row_data == 255)
                    print(f"    Row {row:4d}: {count_visible:5d} visible, {count_opaque:5d} opaque")

    return {
        'alpha_distribution': dict(zip([int(v) for v in unique_alpha], [int(c) for c in counts])),
        'dimensions': {'width': width, 'height': height},
        'total_pixels': total_pixels,
        'visible_pixels': int(alpha_gt_0) if 'alpha_gt_0' in locals() else 0
    }


def main():
    """Main analysis."""
    print("="*70)
    print("Deep HRRR Image Analysis")
    print("="*70)

    western_stats = deep_analyze_image('images/alaska_hrrr_western.webp', 'Western Image')
    eastern_stats = deep_analyze_image('images/alaska_hrrr_eastern.webp', 'Eastern Image')

    # Save stats
    with open('deep_image_stats.json', 'w') as f:
        json.dump({
            'western': western_stats,
            'eastern': eastern_stats
        }, f, indent=2)

    print(f"\n{'='*70}")
    print("Analysis complete. Stats saved to deep_image_stats.json")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
