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


def quantize_image(
    original_path: str,
    depth_path: str,
    palette_path: str
) -> dict[str, Any]:
    """
    Slices depth, maps colors, and generates a block inventory.
    """
    orig_img = cv2.imread(original_path)
    depth_img = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    palette_data = load_palette_data(palette_path)

    if orig_img is None or depth_img is None:
        raise HTTPException(status_code=500, detail="Failed to read images.")

    # 1. Extract BGR arrays for OpenCV math
    colors_list: list[list[int]] = []
    for item in palette_data.get("colors", []):
        r, g, b = item["rgb"]
        colors_list.append([b, g, r])
    palette_bgr = np.array(colors_list, dtype=np.uint8)

    # 2. Depth Layer Extraction (6 layers)
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

    # 4. Generate Brick Inventory (Bonus 1 Prep)
    unique_ids, counts = np.unique(closest_indices, return_counts=True)
    inventory = []
    for idx, count in zip(unique_ids, counts):
        color_info = palette_data["colors"][idx]
        # Convert RGB list to hex string for easy UI rendering
        r, g, b = color_info["rgb"]
        hex_color = f"#{r:02x}{g:02x}{b:02x}"

        inventory.append({
            "name": color_info["name"],
            "hex": hex_color,
            "count": int(count)
        })

    # Sort inventory by highest block count first
    inventory.sort(key=lambda x: x["count"], reverse=True)

    # 5. Save Outputs
    base_name = os.path.basename(original_path)
    out_dir = original_path.replace("uploads", "outputs")
    out_dir = out_dir.replace(base_name, "")

    preview_path = os.path.join(
        out_dir, base_name.replace(".png", "_lego.png"))
    cv2.imwrite(preview_path, lego_img)

    json_path = os.path.join(out_dir, base_name.replace(".png", "_data.json"))
    scene_data = {
        "width": w,
        "height": h,
        "layers": layer_indices.tolist(),
        "colors": quantized_pixels.tolist()
    }
    with open(json_path, "w") as f:
        json.dump(scene_data, f)

    return {
        "width": w,
        "height": h,
        "layers": num_layers,
        "preview_image": preview_path,
        "scene_data": json_path,
        "inventory": inventory
    }
