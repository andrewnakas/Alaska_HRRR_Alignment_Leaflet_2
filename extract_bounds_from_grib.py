#!/usr/bin/env python3
"""
Use GDAL to extract exact bounds from GRIB2

Download a HRRR-Alaska GRIB2 file and use GDAL to:
1. Read the native projection
2. Reproject to WGS84
3. Extract the exact geotransform
4. Get the precise bounds

This will tell us the EXACT bounds the images should have.
"""

import subprocess
import json
from datetime import datetime, timedelta

def get_bounds_from_grib():
    print("="*70)
    print("EXTRACT BOUNDS FROM GRIB2 USING GDAL")
    print("="*70)

    # Use the GRIB2 file we already have via Herbie
    print("\n🔍 Checking for existing GRIB2 file...")

    # First, let's use Herbie to get a file
    try:
        from herbie import Herbie

        # Get recent file
        now = datetime.utcnow()
        for hours_ago in range(0, 24, 3):
            forecast_time = now - timedelta(hours=hours_ago)

            try:
                print(f"\n📥 Trying {forecast_time.strftime('%Y-%m-%d %H:%M')} UTC...")

                H = Herbie(
                    forecast_time,
                    model='hrrrak',
                    product='sfc',
                    fxx=0
                )

                # Download the file
                grib_file = H.download()

                if grib_file and grib_file.exists():
                    print(f"✅ Downloaded: {grib_file}")

                    # Use GDAL to inspect the file
                    print(f"\n📊 Using GDAL to inspect projection...")

                    # Run gdalinfo
                    result = subprocess.run(
                        ['gdalinfo', '-json', str(grib_file)],
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        info = json.loads(result.stdout)

                        print(f"\n✅ GDAL Info retrieved")

                        # Get size
                        size = info.get('size', [])
                        print(f"\nSize: {size}")

                        # Get projection
                        if 'coordinateSystem' in info:
                            wkt = info['coordinateSystem'].get('wkt', '')
                            print(f"\nProjection WKT (truncated):")
                            print(wkt[:500] + "..." if len(wkt) > 500 else wkt)

                        # Get geotransform
                        if 'geoTransform' in info:
                            gt = info['geoTransform']
                            print(f"\nGeoTransform: {gt}")

                            # Calculate corner coordinates
                            width = size[0]
                            height = size[1]

                            # Top-left corner
                            x_tl = gt[0]
                            y_tl = gt[3]

                            # Bottom-right corner
                            x_br = gt[0] + width * gt[1] + height * gt[2]
                            y_br = gt[3] + width * gt[4] + height * gt[5]

                            print(f"\nCorners in native projection:")
                            print(f"  Top-left: ({x_tl:.2f}, {y_tl:.2f})")
                            print(f"  Bottom-right: ({x_br:.2f}, {y_br:.2f})")

                        # Now reproject to WGS84 and get bounds
                        print(f"\n🔄 Reprojecting to WGS84...")

                        output_file = 'hrrr_ak_wgs84.tif'

                        reproject_result = subprocess.run([
                            'gdalwarp',
                            '-t_srs', 'EPSG:4326',
                            '-of', 'GTiff',
                            '-overwrite',
                            str(grib_file),
                            output_file
                        ], capture_output=True, text=True)

                        if reproject_result.returncode == 0:
                            print(f"✅ Reprojected to: {output_file}")

                            # Get info from reprojected file
                            wgs84_result = subprocess.run(
                                ['gdalinfo', '-json', output_file],
                                capture_output=True,
                                text=True
                            )

                            if wgs84_result.returncode == 0:
                                wgs84_info = json.loads(wgs84_result.stdout)

                                size_wgs84 = wgs84_info.get('size', [])
                                gt_wgs84 = wgs84_info.get('geoTransform', [])

                                print(f"\n📐 Reprojected Image Info:")
                                print(f"  Size: {size_wgs84[0]} × {size_wgs84[1]}")
                                print(f"  GeoTransform: {gt_wgs84}")

                                # Calculate WGS84 bounds
                                width_wgs84 = size_wgs84[0]
                                height_wgs84 = size_wgs84[1]

                                west = gt_wgs84[0]
                                north = gt_wgs84[3]

                                pixel_width = gt_wgs84[1]
                                pixel_height = gt_wgs84[5]  # Usually negative

                                east = west + (width_wgs84 * pixel_width)
                                south = north + (height_wgs84 * pixel_height)

                                print(f"\n✨ EXACT WGS84 BOUNDS FROM GDALWARP:")
                                print(f"  West:  {west:.6f}°")
                                print(f"  South: {south:.6f}°")
                                print(f"  East:  {east:.6f}°")
                                print(f"  North: {north:.6f}°")

                                print(f"\n  Leaflet format: [{west:.6f}, {south:.6f}, {east:.6f}, {north:.6f}]")

                                # Save results
                                results = {
                                    'source_grib': str(grib_file),
                                    'native_size': size,
                                    'wgs84_size': size_wgs84,
                                    'wgs84_geotransform': gt_wgs84,
                                    'wgs84_bounds': {
                                        'west': float(west),
                                        'south': float(south),
                                        'east': float(east),
                                        'north': float(north)
                                    },
                                    'leaflet_bounds': [float(west), float(south), float(east), float(north)]
                                }

                                with open('GDAL_EXTRACTED_BOUNDS.json', 'w') as f:
                                    json.dump(results, f, indent=2)

                                print(f"\n💾 Saved to: GDAL_EXTRACTED_BOUNDS.json")
                                print(f"\n{'='*70}\n")

                                return results
                            else:
                                print(f"❌ Error getting WGS84 info: {wgs84_result.stderr}")
                        else:
                            print(f"❌ Reprojection failed: {reproject_result.stderr}")
                    else:
                        print(f"❌ gdalinfo failed: {result.stderr}")

                    break

            except Exception as e:
                print(f"❌ Error: {e}")
                continue

    except ImportError:
        print("❌ Herbie not installed")

    print("\n❌ Could not extract bounds from GRIB2")
    print("Install GDAL: apt-get install gdal-bin python3-gdal")
    return None

if __name__ == '__main__':
    get_bounds_from_grib()
