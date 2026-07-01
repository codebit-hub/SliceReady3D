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
    """Greedy 1D meshing algorithm to merge adjacent identical studs."""
    blocks = []
    max_brick_length = 8

    for y in range(height):
        x = 0
        while x < width:
            current_z = layers[y, x]
            current_color = colors[y * width + x]
            length = 1

            while (x + length < width) and (length < max_brick_length):
                next_z = layers[y, x + length]
                next_color = colors[y * width + x + length]
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
                "w": length,
                "color": current_color.tolist()
            })
            x += length

    return blocks


def quantize_image(
    original_path: str,
    depth_path: str,
    palette_path: str,
    depth_layers: int,
    max_studs: int
) -> dict[str, Any]:
    """Scales, slices depth, and maps colors for the UI."""
    orig_img = cv2.imread(original_path)
    depth_img = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    palette_data = load_palette_data(palette_path)

    if orig_img is None or depth_img is None:
        raise HTTPException(status_code=500, detail="Image read failed.")

    # 1. Resize to max_studs to control volume
    h, w = orig_img.shape[:2]
    scale = max_studs / float(max(h, w))
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))

    orig_img = cv2.resize(
        orig_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    depth_img = cv2.resize(
        depth_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 2. Extract Palette
    colors_list: list[list[int]] = []
    for item in palette_data.get("colors", []):
        r, g, b = item["rgb"]
        colors_list.append([b, g, r])
    palette_bgr = np.array(colors_list, dtype=np.uint8)

    # 3. Depth Layer Slicing
    bin_size = 256.0 / depth_layers
    layer_indices = np.floor(depth_img / bin_size).astype(np.uint8)

    # 4. Color Quantization
    flat_pixels = orig_img.reshape(-1, 3).astype(np.float32)
    flat_palette = palette_bgr.astype(np.float32)

    diff = flat_pixels[:, np.newaxis, :] - flat_palette
    distances = np.sum(diff ** 2, axis=2)
    closest_indices = np.argmin(distances, axis=1)

    quantized_pixels = palette_bgr[closest_indices]
    lego_img = quantized_pixels.reshape(new_h, new_w, 3)

    # 5. Brick Optimization
    opt_blocks = optimize_bricks(layer_indices, quantized_pixels, new_w, new_h)

    # 6. Inventory Generation
    unique_ids, counts = np.unique(closest_indices, return_counts=True)
    inventory = []
    for idx, count in zip(unique_ids, counts):
        color_info = palette_data["colors"][idx]
        r, g, b = color_info["rgb"]
        inventory.append({
            "name": color_info["name"],
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "count": int(count)
        })
    inventory.sort(key=lambda x: x["count"], reverse=True)

    # 7. Save outputs
    base_name = os.path.basename(original_path)
    out_dir = original_path.replace(
        "uploads", "outputs").replace(base_name, "")

    preview_path = os.path.join(
        out_dir, base_name.replace(".png", "_lego.png"))
    cv2.imwrite(preview_path, lego_img)

    json_path = os.path.join(out_dir, base_name.replace(".png", "_data.json"))
    scene_data = {
        "width": new_w, "height": new_h,
        "original_studs": new_w * new_h,
        "optimized_blocks": len(opt_blocks),
        "blocks": opt_blocks
    }
    with open(json_path, "w") as f:
        json.dump(scene_data, f)

    return {
        "width": new_w, "height": new_h, "layers": depth_layers,
        "scene_data": json_path, "inventory": inventory,
        "original_count": new_w * new_h, "optimized_count": len(opt_blocks)
    }
