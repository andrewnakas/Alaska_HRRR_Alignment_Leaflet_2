#!/usr/bin/env python3
"""
STEP 1: Sample GRIB→Image Correspondences and Calculate Affine Transform

This script:
1. Takes known GRIB corner coordinates (lat/lon)
2. Maps them to expected image pixel locations
3. Calculates the affine transform
4. Saves the transform for bounds calculation
"""

import json
import numpy as np
from PIL import Image

def calculate_affine_transform():
    print("="*70)
    print("STEP 1: GRIB→IMAGE AFFINE TRANSFORM")
    print("="*70)

    # Load plan
    with open('ALIGNMENT_DEBUG_PLAN.json', 'r') as f:
        plan = json.load(f)

    print("\n📍 Corner Correspondences:")
    print(f"{'GRIB Point':<20} {'Lat':>10} {'Lon':>10} {'→':^5} {'Image X':>10} {'Image Y':>10}")
    print("-"*70)

    correspondences = []
    for name, corner in plan['corner_correspondences'].items():
        lat = corner['lat']
        lon = corner['lon']
        img_x = corner['expected_image_col']
        img_y = corner['expected_image_row']

        print(f"{name:<20} {lat:>10.3f} {lon:>10.3f} {'→':^5} {img_x:>10} {img_y:>10}")

        correspondences.append({
            'lat': lat,
            'lon': lon,
            'image_x': img_x,
            'image_y': img_y
        })

    # Calculate affine transform
    # We want to solve:
    # image_x = a + b*lon + c*lat
    # image_y = d + e*lon + f*lat

    print("\n📐 Calculating Affine Transform...")

    # Set up the system of equations
    # Using 4 corner points gives us 8 equations (4 for x, 4 for y)

    # For image_x: [1, lon, lat] * [a, b, c]' = image_x
    A_x = []
    b_x = []
    A_y = []
    b_y = []

    for c in correspondences:
        A_x.append([1, c['lon'], c['lat']])
        b_x.append(c['image_x'])
        A_y.append([1, c['lon'], c['lat']])
        b_y.append(c['image_y'])

    A_x = np.array(A_x)
    b_x = np.array(b_x)
    A_y = np.array(A_y)
    b_y = np.array(b_y)

    # Solve using least squares (overdetermined system)
    transform_x, residuals_x, rank_x, s_x = np.linalg.lstsq(A_x, b_x, rcond=None)
    transform_y, residuals_y, rank_y, s_y = np.linalg.lstsq(A_y, b_y, rcond=None)

    a, b, c = transform_x
    d, e, f = transform_y

    print(f"\n✅ Affine Transform Coefficients:")
    print(f"   image_x = {a:.6f} + {b:.6f}*lon + {c:.6f}*lat")
    print(f"   image_y = {d:.6f} + {e:.6f}*lon + {f:.6f}*lat")

    print(f"\n   Residuals: X={residuals_x[0] if len(residuals_x) > 0 else 0:.6f}, Y={residuals_y[0] if len(residuals_y) > 0 else 0:.6f}")

    # Verify the transform with the corner points
    print(f"\n🔍 Verification (predicted vs actual):")
    print(f"{'Corner':<20} {'Pred X':>10} {'Actual X':>10} {'Pred Y':>10} {'Actual Y':>10} {'Error':>10}")
    print("-"*70)

    max_error = 0
    for name, corner in plan['corner_correspondences'].items():
        lat = corner['lat']
        lon = corner['lon']
        actual_x = corner['expected_image_col']
        actual_y = corner['expected_image_row']

        pred_x = a + b*lon + c*lat
        pred_y = d + e*lon + f*lat

        error = np.sqrt((pred_x - actual_x)**2 + (pred_y - actual_y)**2)
        max_error = max(max_error, error)

        print(f"{name:<20} {pred_x:>10.1f} {actual_x:>10} {pred_y:>10.1f} {actual_y:>10} {error:>10.2f}")

    print(f"\nMaximum error: {max_error:.2f} pixels")

    if max_error < 1.0:
        print("✓ Transform is accurate!")
    else:
        print("⚠️ Transform has errors > 1 pixel")

    # Save the transform
    transform_data = {
        'forward_transform': {
            'image_x': {'a': float(a), 'b': float(b), 'c': float(c)},
            'image_y': {'d': float(d), 'e': float(e), 'f': float(f)}
        },
        'correspondences': correspondences,
        'max_error_pixels': float(max_error),
        'image_size': plan['image_size'],
        'data_extent': plan['data_extent']
    }

    with open('correspondence_data.json', 'w') as f:
        json.dump(transform_data, f, indent=2)

    print(f"\n💾 Transform saved to: correspondence_data.json")

    # Now we need to invert the transform to go from image→geo
    # This is a bit complex because we need to solve for lat/lon given image_x, image_y

    print("\n📐 Inverting Transform (Image→Geo)...")

    # From the forward transform:
    # x = a + b*lon + c*lat
    # y = d + e*lon + f*lat

    # Rearrange to solve for lon and lat:
    # b*lon + c*lat = x - a
    # e*lon + f*lat = y - d

    # Matrix form: [b c; e f] * [lon; lat] = [x-a; y-d]

    # Invert the matrix
    M = np.array([[b, c], [e, f]])
    M_inv = np.linalg.inv(M)

    print(f"\n   Inverse matrix:")
    print(f"   [{M_inv[0,0]:.6f}, {M_inv[0,1]:.6f}]")
    print(f"   [{M_inv[1,0]:.6f}, {M_inv[1,1]:.6f}]")

    # For a given image pixel (x, y):
    # [lon; lat] = M_inv * [x-a; y-d]
    # lon = M_inv[0,0] * (x-a) + M_inv[0,1] * (y-d)
    # lat = M_inv[1,0] * (x-a) + M_inv[1,1] * (y-d)

    inv_a = M_inv[0,0]
    inv_b = M_inv[0,1]
    inv_c = M_inv[1,0]
    inv_d = M_inv[1,1]

    print(f"\n   lon = {inv_a:.6f} * (x - {a:.2f}) + {inv_b:.6f} * (y - {d:.2f})")
    print(f"   lat = {inv_c:.6f} * (x - {a:.2f}) + {inv_d:.6f} * (y - {d:.2f})")

    # Add inverse transform to data
    transform_data['inverse_transform'] = {
        'lon': {'inv_a': float(inv_a), 'inv_b': float(inv_b), 'offset_a': float(a), 'offset_d': float(d)},
        'lat': {'inv_c': float(inv_c), 'inv_d': float(inv_d), 'offset_a': float(a), 'offset_d': float(d)}
    }

    with open('correspondence_data.json', 'w') as f:
        json.dump(transform_data, f, indent=2)

    print(f"\n✅ Complete transform saved to: correspondence_data.json")
    print(f"\n{'='*70}\n")

    return transform_data

if __name__ == '__main__':
    calculate_affine_transform()
