# HRRR Alaska Leaflet Alignment Test Harness

Interactive test environment for debugging and perfecting the alignment of HRRR Alaska radar imagery on Leaflet maps.

## The Problem

The HRRR Alaska radar overlay presents unique technical challenges:

1. **Polar Stereographic Projection**: Native GRIB2 data uses polar stereographic projection centered at the North Pole (90°N, 225°E)
2. **International Date Line Crossing**: Alaska spans the ±180° meridian, requiring special handling
3. **Curved Grid Edges**: Polar stereographic grids have curved boundaries when reprojected to WGS84
4. **Boundary Misalignment**: The boundary polygon doesn't perfectly align with image edges

### Current Status

- ✅ Images display correctly with proper date-line wrapping
- ✅ Western and eastern hemisphere images render seamlessly
- ⚠️ **Boundary polygon may not perfectly trace image edges** ← Primary issue to investigate

## Live Demo

Once deployed via GitHub Actions, this test harness will be available at:
```
https://<username>.github.io/Alaska_HRRR_Alignment_Leaflet_2/
```

## Quick Start

### View Locally

```bash
# Clone the repository
git clone <repository-url>
cd Alaska_HRRR_Alignment_Leaflet_2

# Serve locally (Python 3)
python3 -m http.server 8000

# Or use any other local server
# npx http-server -p 8000
```

Open http://localhost:8000 in your browser.

### Update Test Data

To fetch the latest production data:

```bash
curl -s "https://get-hrrr-forecast-pxvei6zf7a-uc.a.run.app" | \
  python3 -c "import sys, json; d=json.load(sys.stdin); alaska = d['data']['forecast_times'][0]['alaska']; print(json.dumps(alaska, indent=2))" \
  > test-data.json
```

## Features

### Visualization Controls

- **Layer Toggle**: Show/hide radar images, boundary polygon, corner markers, and boundary points
- **Opacity Control**: Adjust image transparency for better comparison
- **Navigation Shortcuts**: Quick zoom to Alaska, date line, western/eastern edges
- **Diagnostic Tools**: Log alignment data and measure errors

### Debug Capabilities

1. **Image Corner Markers** (Red): Shows exact bounds of each radar image
2. **Boundary Polygon** (Red Dashed): The calculated boundary that should trace image edges
3. **Boundary Points** (Blue): Individual vertices of the boundary polygon
4. **Wrapped Bounds** (Green): Debug view of date-line wrapping rectangles

### Diagnostic Functions

- **Log Alignment Data**: Outputs detailed coordinate information to console
- **Measure Error**: Calculates alignment discrepancy between images and boundary

## Technical Details

### Data Structure

```json
{
  "western": {
    "image_url": "https://...",
    "bounds": [west, south, east, north]
  },
  "eastern": {
    "image_url": "https://...",
    "bounds": [west, south, east, north]
  },
  "boundary_polygon": [
    {"lat": 41.621, "lon": -174.883},
    ...
  ]
}
```

### Image Overlay Strategy

To handle the date line crossing, each image is displayed in two locations:

1. **Western image**: Displayed at original position AND wrapped +360° longitude
2. **Eastern image**: Displayed at original position AND wrapped -360° longitude

This ensures seamless coverage across the ±180° meridian.

### Projection Information

**Source Projection (GRIB2)**:
```
+proj=stere +lat_0=90 +lon_0=225 +lat_ts=60
+a=6371229 +b=6371229 +x_0=0 +y_0=0
```

**Target Projection**: WGS84 (EPSG:4326)

**Grid**: 1299×919 cells at ~3km resolution

## Alignment Investigation

### Expected Behavior

When alignment is perfect:
- ✅ Red dashed polygon exactly traces the edges of radar images
- ✅ Red corner markers sit on polygon vertices
- ✅ No gaps at the International Date Line
- ✅ Boundary points follow image edges when toggled on

### Common Misalignment Causes

1. **Grid Cell Centers vs Corners**
   - GRIB2 provides cell CENTER coordinates
   - Image bounds should use CORNER coordinates
   - Mismatch causes shift of ~1.5km (half grid cell)

2. **Rectangular vs Curved Boundaries**
   - Simple rectangular bounds don't account for grid curvature
   - Polar stereographic grids have curved edges in lat/lon space
   - Solution: Trace actual grid perimeter from GRIB2 lat/lon arrays

3. **Transform Origin Issues**
   - Reprojection must account for grid cell size
   - Origin should be at first grid cell CORNER, not center

### Debugging Workflow

1. **Visual Inspection**
   - Load the test harness
   - Zoom to different regions (Alaska overview, date line, edges)
   - Toggle boundary polygon and corner markers
   - Look for misalignment

2. **Quantitative Measurement**
   - Click "Measure Error" to calculate alignment discrepancy
   - Check console logs for detailed coordinate data
   - Compare boundary extent with image bounds

3. **Investigate Root Cause**
   - Review backend boundary calculation code
   - Verify GRIB2 coordinate extraction method
   - Check if bounds use grid centers or corners

## Files

- `index.html` - Interactive test harness with Leaflet map
- `test-data.json` - Sample data from production API
- `.github/workflows/deploy.yml` - Auto-deployment to GitHub Pages
- `README.md` - This file

## Testing Checklist

Before considering alignment "perfect":

- [ ] Boundary polygon traces all four image edges accurately
- [ ] No visible misalignment when zoomed in to edges
- [ ] Seamless coverage across the date line (±180°)
- [ ] All four wrapped images display correctly
- [ ] Corner markers align with polygon vertices
- [ ] Boundary extent matches image bounds (< 0.01° error)

## Solution Approaches

If misalignment is detected, consider these fixes (in backend code):

### Approach 1: Use Grid Corner Coordinates

```python
# Instead of using rectangular array_bounds()
# Extract actual grid edge coordinates from GRIB2

# Get corner coordinates (not centers)
first_corner_x = first_center_x - dx / 2.0
first_corner_y = first_center_y - dy / 2.0

# Use corner-based transform
corner_transform = from_origin(first_corner_x, first_corner_y, dx, -dy)
```

### Approach 2: Trace Curved Boundary

```python
# Extract lat/lon of grid perimeter
top_edge = [(lats[0, i], lons[0, i]) for i in range(width)]
right_edge = [(lats[i, -1], lons[i, -1]) for i in range(height)]
bottom_edge = [(lats[-1, i], lons[-1, i]) for i in range(width)][::-1]
left_edge = [(lats[i, 0], lons[i, 0]) for i in range(height)][::-1]

# Create polygon from actual perimeter
boundary_polygon = top_edge + right_edge + bottom_edge + left_edge
```

### Approach 3: Sample Grid Boundary at Higher Density

```python
# Sample boundary at every Nth pixel for smoother curve
sample_rate = 5
boundary_points = []

# Sample all four edges
for i in range(0, width, sample_rate):
    boundary_points.append({'lat': lats[0, i], 'lon': lons[0, i]})  # Top

for i in range(0, height, sample_rate):
    boundary_points.append({'lat': lats[i, -1], 'lon': lons[i, -1]})  # Right

# ... continue for bottom and left edges
```

## Resources

- [HRRR Model Documentation](https://rapidrefresh.noaa.gov/hrrr/)
- [Polar Stereographic Projection](https://proj.org/operations/projections/stere.html)
- [Leaflet Image Overlay](https://leafletjs.com/reference.html#imageoverlay)
- [Rasterio Reprojection](https://rasterio.readthedocs.io/en/latest/topics/reproject.html)

## Production Integration

Backend location (for reference):
```
/functions/main.py
Function: fetch_hrrr_alaska_grib2() (lines ~560-830)
Boundary generation: lines ~741-789
```

Frontend location (for reference):
```
/public/js/app.js
Function: showTerritoryLayer() (lines ~22084)
```

## Contributing

To improve alignment:

1. Make changes to this test harness
2. Test visually and quantitatively
3. Once alignment is perfect, apply fixes to production backend
4. Verify with production data

## License

This is a diagnostic tool for the HRRR Alaska radar alignment project.

---

**Status**: Test harness created. Alignment investigation in progress.

Last updated: 2025-11-09
