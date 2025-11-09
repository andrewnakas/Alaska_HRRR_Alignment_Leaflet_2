#!/usr/bin/env python3
"""
COMPREHENSIVE ALIGNMENT DEBUGGING PLAN

Strategy:
1. Sample known GRIB lat/lon points
2. Find corresponding pixels in the reprojected image
3. Calculate the affine transform from these correspondences
4. Derive the exact bounds from the transform
5. Verify the alignment mathematically

This will tell us EXACTLY what the bounds should be.
"""

import json
import numpy as np
from PIL import Image
import colorsys

def create_alignment_debug_plan():
    print("="*70)
    print("COMPREHENSIVE ALIGNMENT DEBUGGING PLAN")
    print("="*70)

    # Load GRIB2 data
    grib_lats = np.load('hrrr_ak_latitudes.npy')
    grib_lons = np.load('hrrr_ak_longitudes.npy')
    grib_lons_180 = np.where(grib_lons > 180, grib_lons - 360, grib_lons)

    ny, nx = grib_lats.shape
    print(f"\nGRIB Grid: {ny} × {nx}")
    print(f"Lat range: {grib_lats.min():.3f}° to {grib_lats.max():.3f}°")
    print(f"Lon range: {grib_lons_180.min():.3f}° to {grib_lons_180.max():.3f}°")

    # Load image
    img = Image.open('images/alaska_hrrr_western.webp')
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]

    print(f"\nImage: {img_width} × {img_height}")

    # Find data extent in image
    if img.mode == 'RGBA':
        alpha = img_array[:, :, 3]
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        has_color = (r > 10) | (g > 10) | (b > 10)
        data_mask = (alpha > 0) & has_color

    rows_with_data = np.any(data_mask, axis=1)
    cols_with_data = np.any(data_mask, axis=0)

    row_indices = np.where(rows_with_data)[0]
    col_indices = np.where(cols_with_data)[0]

    data_top = row_indices[0]
    data_bottom = row_indices[-1]
    data_left = col_indices[0]
    data_right = col_indices[-1]
    data_height = data_bottom - data_top + 1
    data_width = data_right - data_left + 1

    print(f"Data extent: rows {data_top}-{data_bottom}, cols {data_left}-{data_right}")
    print(f"Data size: {data_width} × {data_height}")

    print("\n" + "="*70)
    print("DEBUGGING STRATEGY")
    print("="*70)

    strategy = """
1. SAMPLE GRID POINT CORRESPONDENCES
   - Take GRIB grid corners (0,0), (0,nx-1), (ny-1,0), (ny-1,nx-1)
   - These have known lat/lon from GRIB2
   - They should map to the data extent corners in the image

   Expected mapping:
   - GRIB(0,0) → Image pixel (data_left, data_top)
   - GRIB(0,nx-1) → Image pixel (data_right, data_top)
   - GRIB(ny-1,0) → Image pixel (data_left, data_bottom)
   - GRIB(ny-1,nx-1) → Image pixel (data_right, data_bottom)

2. CALCULATE AFFINE TRANSFORM
   From the corner correspondences:
   - Image_x = a + b*Lon + c*Lat
   - Image_y = d + e*Lon + f*Lat

   Solve for a,b,c,d,e,f using corner points

3. INVERT TO GET BOUNDS
   From the transform, calculate:
   - What lat/lon corresponds to image pixel (0, 0)?
   - What lat/lon corresponds to image pixel (img_width, img_height)?

   These are the image bounds!

4. VERIFY WITH MORE SAMPLE POINTS
   - Take interior GRIB points
   - Calculate their expected image pixels
   - Compare to actual image data at those locations
   - If colors match, alignment is correct!

5. CREATE VISUAL DEBUG MAP
   Generate a test image showing:
   - GRIB grid overlay
   - Corner markers at GRIB corners
   - Sample point markers
   - Boundary polygon overlay
"""

    print(strategy)

    print("\n" + "="*70)
    print("IMPLEMENTATION PLAN")
    print("="*70)

    implementation = """
FILE 1: sample_grib_image_correspondences.py
- Extract GRIB corner coordinates
- Map to expected image pixels
- Calculate affine transform coefficients
- Output: correspondence_data.json

FILE 2: calculate_bounds_from_transform.py
- Load affine transform
- Invert to get lat/lon for image corners
- Calculate exact bounds
- Output: CALCULATED_BOUNDS.json

FILE 3: verify_alignment_visual.py
- Load GRIB data and image
- Overlay GRIB grid on image
- Mark corner points
- Mark sample interior points
- Show where alignment is off
- Output: alignment_debug.png

FILE 4: test_alignment_accuracy.py
- Sample random GRIB points
- Calculate their image pixel locations
- Check if image colors match expected
- Report alignment accuracy score
- Output: alignment_accuracy_report.json

FILE 5: create_corrected_bounds.py
- Apply all corrections
- Generate final bounds
- Update test-data.json
- Output: FINAL_CORRECTED_BOUNDS.json
"""

    print(implementation)

    print("\n" + "="*70)
    print("EXPECTED OUTCOMES")
    print("="*70)

    outcomes = """
After running this pipeline:

1. We'll have EXACT bounds derived from actual GRIB→Image mapping
2. We'll have visual proof of where alignment issues are
3. We'll have quantitative accuracy metrics
4. We'll have confidence that the math is correct

The final bounds will be:
- Mathematically derived from correspondences
- Verified against actual pixel data
- Tested with multiple sample points
- Ready for production deployment
"""

    print(outcomes)

    # Save the plan
    plan = {
        'grib_grid': {'ny': ny, 'nx': nx},
        'image_size': {'width': img_width, 'height': img_height},
        'data_extent': {
            'top': int(data_top),
            'bottom': int(data_bottom),
            'left': int(data_left),
            'right': int(data_right)
        },
        'corner_correspondences': {
            'GRIB(0,0)': {
                'grib_row': 0, 'grib_col': 0,
                'lat': float(grib_lats[0,0]),
                'lon': float(grib_lons_180[0,0]),
                'expected_image_col': int(data_left),
                'expected_image_row': int(data_top)
            },
            'GRIB(0,nx-1)': {
                'grib_row': 0, 'grib_col': nx-1,
                'lat': float(grib_lats[0,nx-1]),
                'lon': float(grib_lons_180[0,nx-1]),
                'expected_image_col': int(data_right),
                'expected_image_row': int(data_top)
            },
            'GRIB(ny-1,0)': {
                'grib_row': ny-1, 'grib_col': 0,
                'lat': float(grib_lats[ny-1,0]),
                'lon': float(grib_lons_180[ny-1,0]),
                'expected_image_col': int(data_left),
                'expected_image_row': int(data_bottom)
            },
            'GRIB(ny-1,nx-1)': {
                'grib_row': ny-1, 'grib_col': nx-1,
                'lat': float(grib_lats[ny-1,nx-1]),
                'lon': float(grib_lons_180[ny-1,nx-1]),
                'expected_image_col': int(data_right),
                'expected_image_row': int(data_bottom)
            }
        }
    }

    with open('ALIGNMENT_DEBUG_PLAN.json', 'w') as f:
        json.dump(plan, f, indent=2)

    print(f"\n💾 Plan saved to: ALIGNMENT_DEBUG_PLAN.json")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Run: python3 sample_grib_image_correspondences.py")
    print("2. Run: python3 calculate_bounds_from_transform.py")
    print("3. Run: python3 verify_alignment_visual.py")
    print("4. Review alignment_debug.png")
    print("5. Run: python3 test_alignment_accuracy.py")
    print("6. If accuracy > 95%, apply bounds")
    print("\nLet's start with step 1!")
    print("="*70 + "\n")

if __name__ == '__main__':
    create_alignment_debug_plan()
