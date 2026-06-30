import json
import os
from typing import Any

import cv2  # type: ignore
import numpy as np  # type: ignore
from fastapi import HTTPException


def load_palette_data(json_path: str) -> dict[str, Any]:
    """Loads the raw palette JSON data."""
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Palette not found.")
    with open(json_path, "r") as f:
        return json.load(f)


def optimize_bricks(
    layers: np.ndarray,
    colors: np.ndarray,
    width: int,
    height: int
) -> list[dict[str, Any]]:
    """
    Greedy 1D Meshing Algorithm (Bonus 2).
    Scans rows and merges adjacent 1x1 studs of identical color and depth
    into larger standard LEGO bricks (up to 1x8).
    """
    blocks = []
    max_brick_length = 8

    for y in range(height):
        x = 0
        while x < width:
            current_z = layers[y, x]
            current_color = colors[y * width + x]

            # Find how many identical blocks we can merge horizontally
            length = 1

            # FIX: Use the correctly named 'max_brick_length' variable
            while (x + length < width) and (length < max_brick_length):
                next_z = layers[y, x + length]
                next_color = colors[y * width + x + length]

                # If depth and color match, extend the brick
                if next_z == current_z and np.array_equal(
                    current_color, next_color
                ):
                    length += 1
                else:
                    break

            blocks.append({
                "x": x,
                "y": y,
                "z": int(current_z),
                "w": length,  # The physical width of the optimized brick
                "color": current_color.tolist()
            })

            # Skip past the pixels we just merged
            x += length

    return blocks


def quantize_image(
    original_path: str,
    depth_path: str,
    palette_path: str
) -> dict[str, Any]:
    """
    Slices depth, maps colors, and generates the optimized brick data.
    """
    orig_img = cv2.imread(original_path)
    depth_img = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    palette_data = load_palette_data(palette_path)

    if orig_img is None or depth_img is None:
        raise HTTPException(
            status_code=500, detail="Failed to read images."
        )

    # 1. Palette Extraction
    colors_list: list[list[int]] = []
    for item in palette_data.get("colors", []):
        r, g, b = item["rgb"]
        colors_list.append([b, g, r])
    palette_bgr = np.array(colors_list, dtype=np.uint8)

    # 2. Depth Layer Extraction
    num_layers = 6
    bin_size = 256.0 / num_layers
    layer_indices = np.floor(depth_img / bin_size).astype(np.uint8)

    # 3. Color Quantization
    h, w, channels = orig_img.shape
    flat_pixels = orig_img.reshape(-1, channels).astype(np.float32)
    flat_palette = palette_bgr.astype(np.float32)

    diff = flat_pixels[:, np.newaxis, :] - flat_palette
    distances = np.sum(diff ** 2, axis=2)
    closest_indices = np.argmin(distances, axis=1)

    quantized_pixels = palette_bgr[closest_indices]
    lego_img = quantized_pixels.reshape(h, w, channels)

    # 4. Brick Optimization Algorithm (Bonus 2)
    opt_blocks = optimize_bricks(layer_indices, quantized_pixels, w, h)

    # 5. Inventory Generation
    unique_ids, counts = np.unique(closest_indices, return_counts=True)
    inventory = []
    for idx, count in zip(unique_ids, counts):
        color_info = palette_data["colors"][idx]
        r, g, b = color_info["rgb"]
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        inventory.append({
            "name": color_info["name"],
            "hex": hex_color,
            "count": int(count)
        })
    inventory.sort(key=lambda x: x["count"], reverse=True)

    # 6. Save Outputs
    base_name = os.path.basename(original_path)
    out_dir = original_path.replace("uploads", "outputs")
    out_dir = out_dir.replace(base_name, "")

    preview_name = base_name.replace(".png", "_lego.png")
    preview_path = os.path.join(out_dir, preview_name)
    cv2.imwrite(preview_path, lego_img)

    json_name = base_name.replace(".png", "_data.json")
    json_path = os.path.join(out_dir, json_name)
    scene_data = {
        "width": w,
        "height": h,
        "original_studs": w * h,
        "optimized_blocks": len(opt_blocks),
        "blocks": opt_blocks
    }
    with open(json_path, "w") as f:
        json.dump(scene_data, f)

    # FIX: Stacked return dictionary to perfectly respect line length limits
    return {
        "width": w,
        "height": h,
        "layers": num_layers,
        "preview_image": preview_path,
        "scene_data": json_path,
        "inventory": inventory,
        "original_count": w * h,
        "optimized_count": len(opt_blocks)
    }
