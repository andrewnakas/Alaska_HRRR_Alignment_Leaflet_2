#!/usr/bin/env python3
"""
Get HRRR-Alaska Grid Information from Actual GRIB2 Data

Uses Herbie to download real HRRR-Alaska data and extract:
- Exact grid dimensions
- Precise lat/lon coordinates for every grid point
- Projection parameters
- Geographic bounds

This gives us the TRUTH for alignment.

Usage:
    python3 get_hrrr_ak_grid.py
"""

import json
import numpy as np
from datetime import datetime, timedelta

try:
    from herbie import Herbie
    import cfgrib
    import xarray as xr
    print("✅ Herbie and dependencies loaded")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Installing additional dependencies...")
    import subprocess
    subprocess.run(["pip3", "install", "--quiet", "cfgrib", "xarray"], check=False)
    from herbie import Herbie
    import cfgrib
    import xarray as xr

def get_hrrr_alaska_grid():
    """Download recent HRRR-Alaska file and extract grid info."""

    print("\n" + "="*70)
    print("HRRR-Alaska Grid Information from GRIB2")
    print("="*70)

    # Try to get a recent HRRR-Alaska file
    # HRRR-Alaska runs every 3 hours
    now = datetime.utcnow()

    # Try recent forecast times (last 24 hours)
    for hours_ago in range(0, 24, 3):
        forecast_time = now - timedelta(hours=hours_ago)

        try:
            print(f"\n🔍 Trying {forecast_time.strftime('%Y-%m-%d %H:%M')} UTC...")

            # Create Herbie object for HRRR-Alaska
            H = Herbie(
                forecast_time,
                model='hrrrak',  # HRRR-Alaska
                product='sfc',   # Surface fields
                fxx=0            # Analysis (0-hour forecast)
            )

            print(f"   Source: {H.grib}")

            # Download and open the GRIB2 file
            # Try to get reflectivity or temperature field
            ds = H.xarray('REFC:entire')  # Composite reflectivity

            if ds is None:
                print("   Reflectivity not available, trying temperature...")
                ds = H.xarray('TMP:2 m')  # 2m temperature

            if ds is None:
                print("   ❌ No data available")
                continue

            print(f"   ✅ Data loaded!")

            # Extract grid information
            print(f"\n📊 Grid Information:")
            print(f"   Dimensions: {dict(ds.dims)}")

            # Get lat/lon coordinates
            if 'latitude' in ds.coords and 'longitude' in ds.coords:
                lats = ds.latitude.values
                lons = ds.longitude.values

                print(f"\n🌍 Geographic Extent:")
                print(f"   Latitude range:  {lats.min():.6f}° to {lats.max():.6f}°")
                print(f"   Longitude range: {lons.min():.6f}° to {lons.max():.6f}°")
                print(f"   Latitude span:   {lats.max() - lats.min():.6f}°")
                print(f"   Longitude span:  {lons.max() - lons.min():.6f}°")

                # Get projection info
                if hasattr(ds, 'crs') or 'crs' in ds.attrs:
                    print(f"\n📐 Projection Info:")
                    if 'crs' in ds.attrs:
                        print(f"   {ds.attrs['crs']}")

                # Get grid mapping if available
                for var_name in ds.data_vars:
                    var = ds[var_name]
                    if 'grid_mapping' in var.attrs:
                        grid_mapping_name = var.attrs['grid_mapping']
                        if grid_mapping_name in ds.coords:
                            gm = ds.coords[grid_mapping_name]
                            print(f"\n   Grid Mapping: {grid_mapping_name}")
                            for attr, value in gm.attrs.items():
                                print(f"     {attr}: {value}")
                        break

                # Calculate edge coordinates (corners and boundaries)
                print(f"\n🎯 Grid Corners:")
                ny, nx = lats.shape

                corners = {
                    'NW': (lats[0, 0], lons[0, 0]),
                    'NE': (lats[0, -1], lons[0, -1]),
                    'SW': (lats[-1, 0], lons[-1, 0]),
                    'SE': (lats[-1, -1], lons[-1, -1])
                }

                for corner, (lat, lon) in corners.items():
                    print(f"   {corner}: ({lat:.6f}°, {lon:.6f}°)")

                # Get boundary points (every 10th point along edges)
                print(f"\n🔲 Boundary Polygon (sampled every 10 points):")
                boundary_points = []

                # Top edge (west to east)
                for i in range(0, nx, 10):
                    boundary_points.append({'lat': float(lats[0, i]), 'lon': float(lons[0, i])})

                # Right edge (north to south)
                for i in range(0, ny, 10):
                    boundary_points.append({'lat': float(lats[i, -1]), 'lon': float(lons[i, -1])})

                # Bottom edge (east to west)
                for i in range(nx-1, -1, -10):
                    boundary_points.append({'lat': float(lats[-1, i]), 'lon': float(lons[-1, i])})

                # Left edge (south to north)
                for i in range(ny-1, -1, -10):
                    boundary_points.append({'lat': float(lats[i, 0]), 'lon': float(lons[i, 0])})

                print(f"   Generated {len(boundary_points)} boundary points")

                # Save results
                results = {
                    'source': str(H.grib),
                    'forecast_time': forecast_time.isoformat(),
                    'grid_dimensions': {
                        'ny': int(ny),
                        'nx': int(nx)
                    },
                    'geographic_extent': {
                        'lat_min': float(lats.min()),
                        'lat_max': float(lats.max()),
                        'lon_min': float(lons.min()),
                        'lon_max': float(lons.max())
                    },
                    'corners': {k: {'lat': float(v[0]), 'lon': float(v[1])} for k, v in corners.items()},
                    'boundary_polygon': boundary_points,
                    'bounds_wsen': [
                        float(lons.min()),  # west
                        float(lats.min()),  # south
                        float(lons.max()),  # east
                        float(lats.max())   # north
                    ]
                }

                # Save full lat/lon grids
                print(f"\n💾 Saving full lat/lon grids...")
                np.save('hrrr_ak_latitudes.npy', lats)
                np.save('hrrr_ak_longitudes.npy', lons)
                print(f"   Saved: hrrr_ak_latitudes.npy ({lats.shape})")
                print(f"   Saved: hrrr_ak_longitudes.npy ({lons.shape})")

                with open('hrrr_ak_grid_info.json', 'w') as f:
                    json.dump(results, f, indent=2)

                print(f"\n📝 Results saved to: hrrr_ak_grid_info.json")

                # Print recommended bounds
                print(f"\n{'='*70}")
                print("RECOMMENDED BOUNDS FOR LEAFLET")
                print(f"{'='*70}")
                print(f"\nFor images reprojected to WGS84 covering this domain:")
                print(f"  bounds: [{results['bounds_wsen'][0]:.6f}, {results['bounds_wsen'][1]:.6f}, {results['bounds_wsen'][2]:.6f}, {results['bounds_wsen'][3]:.6f}]")
                print(f"\n  Or in [west, south, east, north] format:")
                print(f"  [{lons.min():.6f}, {lats.min():.6f}, {lons.max():.6f}, {lats.max():.6f}]")

                print(f"\n{'='*70}\n")

                return results
            else:
                print("   ❌ No lat/lon coordinates found")
                continue

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    print("\n❌ Could not retrieve HRRR-Alaska data")
    print("   Try manually checking: https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/")
    return None


if __name__ == '__main__':
    get_hrrr_alaska_grid()
