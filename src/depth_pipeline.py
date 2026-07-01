import os
import cv2  # type: ignore
import numpy as np  # type: ignore
from fastapi import HTTPException


def estimate_depth(input_path: str, output_path: str) -> str:
    """Generates a depth map using Luminance + Edge heuristic."""
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Image not found.")

    img = cv2.imread(input_path)
    if img is None:
        raise HTTPException(
            status_code=400,
            detail="Failed to decode the uploaded image."
        )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    edges = cv2.magnitude(grad_x, grad_y)
    edges_norm = np.zeros_like(edges)
    cv2.normalize(edges, edges_norm, 0.0, 255.0, cv2.NORM_MINMAX)
    edges_8u = edges_norm.astype(np.uint8)

    depth_map = cv2.addWeighted(gray, 0.5, edges_8u, 0.5, 0.0)
    smoothed_depth = cv2.GaussianBlur(depth_map, (9, 9), 0.0)

    success: bool = cv2.imwrite(output_path, smoothed_depth)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to write depth map to disk."
        )

    return output_path
