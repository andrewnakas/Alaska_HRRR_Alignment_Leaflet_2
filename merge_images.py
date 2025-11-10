#!/usr/bin/env python3
"""
Merge western and eastern HRRR Alaska images into one composite image.
"""

from PIL import Image
import numpy as np

print("=" * 70)
print("MERGING WESTERN AND EASTERN IMAGES")
print("=" * 70)

# Load images
print("\n📂 Loading images...")
western_img = Image.open('images/alaska_hrrr_western.webp')
eastern_img = Image.open('images/alaska_hrrr_eastern.webp')

print(f"✓ Western: {western_img.width} x {western_img.height}")
print(f"✓ Eastern: {eastern_img.width} x {eastern_img.height}")

# Convert to numpy arrays
western_array = np.array(western_img)
eastern_array = np.array(eastern_img)

# They should be the same size
if western_array.shape != eastern_array.shape:
    print(f"⚠ Warning: Images have different sizes!")
    print(f"   Western: {western_array.shape}")
    print(f"   Eastern: {eastern_array.shape}")
    # Resize eastern to match western if needed
    if eastern_img.size != western_img.size:
        eastern_img = eastern_img.resize(western_img.size, Image.LANCZOS)
        eastern_array = np.array(eastern_img)
        print(f"✓ Resized eastern to match western")

print("\n🔀 Merging images...")

# Get alpha channels
if western_array.shape[2] == 4:  # RGBA
    western_alpha = western_array[:, :, 3]
    eastern_alpha = eastern_array[:, :, 3]

    # Create composite
    # Where western has data (alpha > 0), use western
    # Where western is transparent but eastern has data, use eastern
    composite = western_array.copy()

    # Find pixels where western is transparent but eastern has data
    western_transparent = western_alpha == 0
    eastern_has_data = eastern_alpha > 0
    use_eastern = western_transparent & eastern_has_data

    # Replace those pixels with eastern data
    composite[use_eastern] = eastern_array[use_eastern]

    # Also blend where both have data (average them)
    both_have_data = (western_alpha > 0) & (eastern_alpha > 0)
    if np.any(both_have_data):
        # Blend with alpha weighting
        w_weight = western_alpha[both_have_data].astype(float) / 255.0
        e_weight = eastern_alpha[both_have_data].astype(float) / 255.0
        total_weight = w_weight + e_weight

        # Avoid division by zero
        valid = total_weight > 0
        w_weight[valid] = w_weight[valid] / total_weight[valid]
        e_weight[valid] = e_weight[valid] / total_weight[valid]

        # Blend RGB channels
        for c in range(3):  # RGB
            blended = (western_array[both_have_data, c].astype(float) * w_weight +
                      eastern_array[both_have_data, c].astype(float) * e_weight)
            composite[both_have_data, c] = blended.astype(np.uint8)

        # Blend alpha (take maximum)
        composite[both_have_data, 3] = np.maximum(
            western_array[both_have_data, 3],
            eastern_array[both_have_data, 3]
        )

    pixels_from_eastern = np.sum(use_eastern)
    pixels_from_western = np.sum((western_alpha > 0) & ~use_eastern)
    pixels_blended = np.sum(both_have_data)

    print(f"✓ Pixels from western: {pixels_from_western:,}")
    print(f"✓ Pixels from eastern: {pixels_from_eastern:,}")
    print(f"✓ Pixels blended: {pixels_blended:,}")

else:
    # No alpha channel, just use western
    composite = western_array
    print("⚠ No alpha channel, using western only")

# Create output image
print("\n💾 Saving composite image...")
composite_img = Image.fromarray(composite)
composite_img.save('images/alaska_hrrr_combined.webp', 'WEBP', quality=95)

print(f"✓ Saved to: images/alaska_hrrr_combined.webp")
print(f"   Size: {composite_img.width} x {composite_img.height}")

# Show file size
import os
western_size = os.path.getsize('images/alaska_hrrr_western.webp') / 1024
eastern_size = os.path.getsize('images/alaska_hrrr_eastern.webp') / 1024
combined_size = os.path.getsize('images/alaska_hrrr_combined.webp') / 1024

print(f"\n📊 File sizes:")
print(f"   Western: {western_size:.1f} KB")
print(f"   Eastern: {eastern_size:.1f} KB")
print(f"   Combined: {combined_size:.1f} KB")

print("\n" + "=" * 70)
print("✓ COMPLETE!")
print("=" * 70)
print("\nUse this single image in your map overlays instead of")
print("loading both western and eastern separately.")
