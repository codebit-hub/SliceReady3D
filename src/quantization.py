import json
import os
from typing import Any

import cv2  # type: ignore
import numpy as np  # type: ignore
from fastapi import HTTPException


def load_lego_palette(json_path: str) -> np.ndarray:
    """
    Loads the official LEGO palette from JSON.
    Returns a NumPy array of BGR colors for OpenCV compatibility.
    Using Python 3.13 built-in typing (dict, list).
    """
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Palette not found.")

    with open(json_path, "r") as f:
        data: dict[str, Any] = json.load(f)

    colors: list[list[int]] = []
    for item in data.get("colors", []):
        # Extract RGB, but OpenCV uses BGR, so we reverse the order
        r, g, b = item["rgb"]
        colors.append([b, g, r])

    # Return as an 8-bit unsigned integer array
    return np.array(colors, dtype=np.uint8)


def quantize_image(
    original_path: str,
    depth_path: str,
    palette_path: str
) -> dict[str, Any]:
    """
    Slices the depth map into layers and maps colors to the LEGO palette.
    Outputs a 2D preview image and a JSON blueprint for 3D rendering.
    """
    # 1. Load images and the color palette
    orig_img = cv2.imread(original_path)
    depth_img = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    palette_bgr = load_lego_palette(palette_path)

    if orig_img is None or depth_img is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to read images for quantization."
        )

    # 2. Depth Layer Extraction (Mandatory V.3)
    num_layers = 6
    bin_size = 256.0 / num_layers

    # Floor division creates discrete layers (0, 1, 2, 3, 4, 5)
    layer_indices = np.floor(depth_img / bin_size).astype(np.uint8)

    # 3. LEGO Color Reconstruction (Mandatory V.4)
    # Flatten the image to a 2D array of pixels for faster math
    h, w, channels = orig_img.shape
    flat_pixels = orig_img.reshape(-1, channels).astype(np.float32)
    flat_palette = palette_bgr.astype(np.float32)

    # Broadcast to find the Euclidean distance between every pixel
    # and every official LEGO color in the palette.
    diff = flat_pixels[:, np.newaxis, :] - flat_palette
    distances = np.sum(diff ** 2, axis=2)

    # Find the index of the closest LEGO color for each pixel
    closest_indices = np.argmin(distances, axis=1)

    # Map the indices back to the actual BGR values
    quantized_pixels = palette_bgr[closest_indices]

    # Reshape back to the original image dimensions for the 2D preview
    lego_img = quantized_pixels.reshape(h, w, channels)

    # 4. Save a 2D visual preview of the LEGO-ified image
    base_name = os.path.basename(original_path)
    # Safely replace directory paths
    out_dir = original_path.replace("uploads", "outputs")
    out_dir = out_dir.replace(base_name, "")

    preview_name = base_name.replace(".png", "_lego.png")
    preview_path = os.path.join(out_dir, preview_name)
    cv2.imwrite(preview_path, lego_img)

    # 5. Save the 3D structural blueprint (JSON)
    # This solves the F841 error: we now actively save the layers!
    json_name = base_name.replace(".png", "_data.json")
    json_path = os.path.join(out_dir, json_name)

    # Bundle the width, height, colors, and Z-depth layers
    scene_data = {
        "width": w,
        "height": h,
        "layers": layer_indices.tolist(),
        "colors": quantized_pixels.tolist()
    }
    with open(json_path, "w") as f:
        json.dump(scene_data, f)

    # 6. Return metadata to the controller
    return {
        "width": w,
        "height": h,
        "preview_image": preview_path,
        "scene_data": json_path
    }
