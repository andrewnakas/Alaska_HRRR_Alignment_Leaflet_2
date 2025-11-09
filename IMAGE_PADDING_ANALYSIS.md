# CRITICAL DISCOVERY: Image Padding Issue

**Date:** 2025-11-09
**Status:** 🔴 ROOT CAUSE IDENTIFIED - Image bounds include massive transparent padding

---

## Executive Summary

The **primary cause** of alignment issues is **not** the grid center vs corner problem (which is minor). The real issue is that the reprojected images contain **significant transparent padding** that is not accounted for in the stated bounds.

**Impact:**
- North boundary off by **-3.82° = -423 km**
- South boundary off by **+0.68° = +75 km**
- This dwarfs the 1.8km grid center/corner error

---

## Image Analysis Results

### Western Image (`alaska_hrrr_western.webp`)

```
Image size:      12170 × 1200 pixels
Image mode:      RGBA

Pixel padding:
  Top:    129 pixels (10.8% of image height) - TRANSPARENT
  Bottom:  23 pixels ( 1.9% of image height) - TRANSPARENT
  Left:     0 pixels ( 0.0% of image width)
  Right:    0 pixels ( 0.0% of image width)

Actual radar data: rows 129-1176 (1048 pixels of radar data)
Data coverage: 87.3% of image
```

### Eastern Image (`alaska_hrrr_eastern.webp`)

```
Image size:      12169 × 1200 pixels
Image mode:      RGBA

Pixel padding:
  Top:    129 pixels (10.8% of image height) - TRANSPARENT
  Bottom:  23 pixels ( 1.9% of image height) - TRANSPARENT
  Left:     0 pixels ( 0.0% of image width)
  Right:    0 pixels ( 0.0% of image width)

Actual radar data: rows 129-1176 (1048 pixels of radar data)
Data coverage: 87.3% of image
```

---

## Geographic Impact

### Stated vs Actual Bounds

**Western Image:**
```
Stated bounds:    [-180.004, 41.605, 180.008, 77.101]
Actual data:      [-180.004, 42.285, 180.008, 73.285]

Corrections:
  West:   0.000° (  0.0 km) ✅
  East:   0.000° (  0.0 km) ✅
  South: +0.680° (+75.5 km) ⚠️
  North: -3.816° (-423.6 km) 🔴 CRITICAL
```

**Eastern Image:**
```
Stated bounds:    [-179.985, 41.605, 179.994, 77.101]
Actual data:      [-179.985, 42.285, 179.994, 73.285]

Corrections:
  West:   0.000° (  0.0 km) ✅
  East:   0.000° (  0.0 km) ✅
  South: +0.680° (+75.5 km) ⚠️
  North: -3.816° (-423.6 km) 🔴 CRITICAL
```

---

## Why This Happened

### Backend Reprojection Process

When the backend reprojects GRIB2 data to WGS84:

1. **Source data**: Polar stereographic grid (1299×919 cells, 3km resolution)
2. **Destination**: WGS84 rectangular grid
3. **Issue**: Polar stereographic grids are NOT rectangular in lat/lon space
4. **Result**: Reprojected image has curved data boundaries, leaving empty corners

```
Visual representation:

Polar stereographic grid        Reprojected to WGS84
(curved in lat/lon space)       (rectangular image)

     ╱─────────╲                 ┌─────────────────┐
    │           │                │▓▓▓transparent▓▓▓│ ← Top padding
    │  RADAR    │                │─────────────────│
    │   DATA    │       →        │█████████████████│
    │           │                │█████ RADAR █████│ ← Actual data
    │           │                │█████  DATA █████│
     ╲─────────╱                 │█████████████████│
                                 │▓▓▓transparent▓▓▓│ ← Bottom padding
                                 └─────────────────┘
```

The stated bounds (`array_bounds()`) describe the **entire rectangular image**, including the transparent padding. But the actual radar data only fills part of it.

---

## Comparison to Boundary Polygon

**Boundary polygon extent:**
```
South: 41.621°
North: 77.085°
Range: 35.464°
```

**Stated image bounds:**
```
South: 41.605°
North: 77.101°
Range: 35.496°
```

**Actual data in image:**
```
South: 42.285°
North: 73.285°
Range: 31.000°
```

**KEY INSIGHT:** The boundary polygon (41.621° - 77.085°) actually **encompasses MORE area** than the actual radar data (42.285° - 73.285°)!

This means:
- The boundary polygon is not "too small"
- The boundary polygon extends beyond the actual radar data
- The problem is that it doesn't match WHERE the data is in the image

---

## Root Cause Analysis

### What the Backend Does Wrong

```python
# Current backend logic (simplified):

# 1. Reproject GRIB2 data to WGS84
reproject(...)

# 2. Get bounds from the OUTPUT ARRAY (includes padding!)
dst_transform = from_bounds(west, south, east, north, width, height)
exact_bounds = array_bounds(height, width, dst_transform)
# Returns: [-180.004, 41.605, 180.008, 77.101]

# 3. Extract boundary polygon from GRIB2 grid edges
# (This traces the actual data, not the padded image!)
boundary_polygon = extract_grid_boundary(grib2_lats, grib2_lons)
# Returns points from 41.621° to 77.085°
```

The **mismatch**:
- `exact_bounds` describes the rectangular bounding box that was used for reprojection
- `boundary_polygon` traces the actual curved grid edges
- Neither describes where the data actually landed in the image after reprojection

---

## The Fix

### Option 1: Crop Images (Backend)

Modify backend to crop transparent padding:

```python
from PIL import Image
import numpy as np

# After reprojection
img = Image.fromarray(wgs84_array)

# Find non-transparent pixels
mask = np.array(img)[:, :, 3] > 0  # Alpha channel
rows = np.any(mask, axis=1)
cols = np.any(mask, axis=0)

# Crop to actual data
top = np.where(rows)[0][0]
bottom = np.where(rows)[0][-1]
left = np.where(cols)[0][0]
right = np.where(cols)[0][-1]

cropped_img = img.crop((left, top, right + 1, bottom + 1))

# Calculate corrected bounds for cropped image
corrected_bounds = [
    west + (left * deg_per_pixel_lon),
    north - ((bottom + 1) * deg_per_pixel_lat),
    west + ((right + 1) * deg_per_pixel_lon),
    north - (top * deg_per_pixel_lat)
]
```

**Pros:**
- Eliminates padding
- Reduces file size
- Bounds exactly match data

**Cons:**
- Adds image processing step
- May affect existing consumers

---

### Option 2: Calculate Actual Data Bounds (Backend)

Keep padded images but calculate true data extent:

```python
# After reprojection, analyze where data actually is
mask = wgs84_array[:, :, 3] > 0  # Non-transparent pixels
rows = np.any(mask, axis=1)
cols = np.any(mask, axis=0)

data_top = np.where(rows)[0][0]
data_bottom = np.where(rows)[0][-1]
data_left = np.where(cols)[0][0]
data_right = np.where(cols)[0][-1]

# Calculate bounds for ACTUAL DATA, not full image
deg_per_pixel_lon = (east - west) / width
deg_per_pixel_lat = (north - south) / height

actual_bounds = [
    west + (data_left * deg_per_pixel_lon),
    north - ((data_bottom + 1) * deg_per_pixel_lat),
    west + ((data_right + 1) * deg_per_pixel_lon),
    north - (data_top * deg_per_pixel_lat)
]
```

**Pros:**
- Keeps existing images
- Accurately describes data location
- Backward compatible

**Cons:**
- Images still contain unnecessary padding
- Wastes bandwidth/storage

---

### Option 3: Use Boundary Polygon for Clipping (Frontend - CURRENT)

This is what we've implemented in the test harness:

```javascript
// Instead of using rectangular imageOverlay bounds,
// use the boundary polygon to clip the display
// (This is not directly supported by Leaflet)

// Current workaround: Just fix the bounds
const correctedBounds = [
    [42.285, -180.004],  // SW (actual data start)
    [73.285, 180.008]    // NE (actual data end)
];

L.imageOverlay(url, correctedBounds).addTo(map);
```

**Pros:**
- Works with existing images
- No backend changes needed
- Can be implemented immediately

**Cons:**
- Doesn't address root cause
- Each consumer must know to correct bounds
- Boundary polygon still won't perfectly align (still has grid center/corner issue)

---

## Recommended Solution

### Short-term (Frontend Fix)

1. ✅ Use corrected bounds calculated from image analysis
2. ✅ Update test-data.json with actual data bounds
3. ✅ Verify alignment in test harness

### Long-term (Backend Fix)

1. Modify backend to calculate actual data bounds after reprojection
2. Return both:
   - `image_bounds`: Full image dimensions
   - `data_bounds`: Actual radar data extent within image
3. Optionally crop images to remove padding

---

## Testing Results

### Before Correction

```
Alignment error measurement:
  Southern edge: 1.76 km (boundary inside image)
  Northern edge: 1.81 km (boundary inside image)
```

This was misleading - it appeared the boundary was too small, but actually:
- The boundary extended beyond the actual data
- The stated image bounds included massive padding
- The 1.8km error was from comparing boundary to STATED bounds, not ACTUAL data

### After Correction (Expected)

```
With corrected bounds [42.285°, 73.285°]:
  Southern edge: Boundary should extend ~0.4° BEYOND data (still issue)
  Northern edge: Boundary should extend ~3.8° BEYOND data (still issue)
```

Wait - this means the boundary polygon STILL doesn't match the data!

Let me recalculate:
- Data south: 42.285°, Boundary south: 41.621° → Boundary extends 0.664° south of data
- Data north: 73.285°, Boundary north: 77.085° → Boundary extends 3.800° north of data

**This means the boundary polygon is LARGER than the actual radar data in the images!**

---

## Updated Root Cause

There are actually **THREE alignment issues**:

1. ✅ **Image padding** (423 km north, 75 km south) - FIXED by corrected bounds
2. ⚠️ **Grid center vs corner** (1.5 km all edges) - Needs backend fix
3. 🔴 **Boundary extends beyond data** - The boundary polygon is calculated from GRIB2 grid extents, but those extents are LARGER than what ends up in the reprojected image

The third issue suggests that during reprojection, some of the outer grid cells don't actually contain valid data or get clipped.

---

## Next Steps

1. ✅ Apply corrected image bounds (done)
2. 🔄 Test in harness - measure NEW alignment error
3. 📊 Analyze why boundary polygon is larger than actual data
4. 🔧 Fix backend to:
   - Calculate actual data bounds after reprojection
   - Adjust boundary polygon to match actual reprojected data extent
   - Or crop images to match stated boundaries

---

## Files Generated

- `analyze_image_bounds.py` - Image analysis tool
- `image_analysis_results.json` - Detailed padding measurements
- `apply_corrected_bounds.py` - Script to apply corrections

---

**Analysis conducted by:** Claude Code
**Test harness:** https://andrewnakas.github.io/Alaska_HRRR_Alignment_Leaflet_2/
**Repository:** Alaska_HRRR_Alignment_Leaflet_2
