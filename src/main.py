import os
from typing import Annotated, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.depth_pipeline import estimate_depth
from src.quantization import quantize_image

app = FastAPI(title="SliceReady3D API")

UPLOAD_DIR = "src/uploads"
OUTPUT_DIR = "src/outputs"
PALETTE_PATH = "src/palette.json"
STATIC_DIR = "src/static"

# Ensure all necessary directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static directories so the browser can request these files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/")
async def serve_index() -> FileResponse:
    """
    Serves the main frontend HTML file at the root URL.
    This fulfills Mandatory V.6 User Experience flow.
    """
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(
            status_code=404,
            detail="Frontend index.html not found."
        )
    return FileResponse(index_path)


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

    # 3. Quantize and Map to LEGO Colors
    try:
        mosaic_data: dict[str, Any] = quantize_image(
            original_path,
            saved_depth_path,
            PALETTE_PATH
        )
    except Exception as e:
        error_msg = f"Quantization failed: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

    # 4. Return combined results to the frontend
    return JSONResponse(
        status_code=200,
        content={
            "message": "Processing complete",
            "original": original_path,
            "depth_map": saved_depth_path,
            "mosaic_data": mosaic_data
        }
    )
