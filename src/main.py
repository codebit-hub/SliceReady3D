import os
from typing import Annotated, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from src.depth_pipeline import estimate_depth
from src.quantization import quantize_image  # <-- New import

app = FastAPI(title="SliceReady3D API")

UPLOAD_DIR = "src/uploads"
OUTPUT_DIR = "src/outputs"
# Path to our new JSON palette
PALETTE_PATH = "src/palette.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.post("/api/upload")
async def upload_image(
    file: Annotated[UploadFile, File(...)],
) -> JSONResponse:
    """
    Handles upload, estimates depth, and quantizes the image.
    """
    allowed_types: set[str] = {"image/png", "image/jpeg", "image/webp"}
    content_type: str = file.content_type or ""

    if content_type not in allowed_types:
        error_msg = (
            f"Invalid file type: {content_type}. "
            "Only PNG, JPEG, and WEBP allowed."
        )
        raise HTTPException(status_code=400, detail=error_msg)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    # 1. Save Original
    original_path: str = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(original_path, "wb") as buffer:
            content: bytes = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save error: {str(e)}")

    # 2. Generate Depth
    depth_filename = f"depth_{file.filename}"
    depth_path: str = os.path.join(OUTPUT_DIR, depth_filename)

    try:
        saved_depth_path = estimate_depth(original_path, depth_path)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Depth error: {str(e)}")

    # 3. Quantize and Map to LEGO Colors (New Step)
    try:
        mosaic_data: Dict[str, Any] = quantize_image(
            original_path,
            saved_depth_path,
            PALETTE_PATH
        )
    except Exception as e:
        error_msg = f"Quantization failed: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

    # 4. Return combined results
    return JSONResponse(
        status_code=200,
        content={
            "message": "Processing complete",
            "original": original_path,
            "depth_map": saved_depth_path,
            "mosaic_data": mosaic_data
        }
    )
