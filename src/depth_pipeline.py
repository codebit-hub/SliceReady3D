import os
import cv2  # type: ignore
import numpy as np  # type: ignore
from fastapi import HTTPException


def estimate_depth(input_path: str, output_path: str) -> str:
    """
    Generates a depth map using a local Luminance + Edge heuristic.
    Requires no internet and runs efficiently on minimal RAM.
    """
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Image not found.")

    # Step 1: Read the image from disk
    img = cv2.imread(input_path)
    if img is None:
        raise HTTPException(
            status_code=400,
            detail="Failed to decode the uploaded image."
        )

    # Step 2: Extract Luminance (brightness)
    # Convert the image to grayscale. In naive depth estimation,
    # brighter pixels are often interpreted as being closer.
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Step 3: Extract Edges (sharpness)
    # We use the Sobel operator to find gradients (edges).
    # Objects in focus in the foreground have sharper edges.
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    # Calculate the magnitude of the gradients to get the edge map
    edges = cv2.magnitude(grad_x, grad_y)

    # Normalize the edge map so values fall cleanly between 0.0 and 255.0
    edges_norm = np.zeros_like(edges)
    cv2.normalize(edges, edges_norm, 0.0, 255.0, cv2.NORM_MINMAX)

    # FIX: Use .astype() so MyPy knows this remains an ndarray
    edges_8u = edges_norm.astype(np.uint8)

    # Step 4: Combine the Heuristics
    # FIX: Ensure all weight and gamma parameters are explicit floats
    depth_map = cv2.addWeighted(gray, 0.5, edges_8u, 0.5, 0.0)

    # Step 5: Smooth the Depth Map
    # Ensure the sigma value (0.0) is a float as well
    smoothed_depth = cv2.GaussianBlur(depth_map, (9, 9), 0.0)

    # Step 6: Save the generated depth map
    success: bool = cv2.imwrite(output_path, smoothed_depth)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to write depth map to disk."
        )

    return output_path
