import os
import shutil
from typing import Annotated, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.depth_pipeline import estimate_depth
from src.quantization import quantize_image

app = FastAPI(title="SliceReady3D API")

UPLOAD_DIR = "src/uploads"
OUTPUT_DIR = "src/outputs"
PALETTE_PATH = "src/palette.json"
STATIC_DIR = "src/static"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB maximum file size limit


@app.get("/")
async def serve_index() -> FileResponse:
    """Serves the main frontend HTML file."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Index not found.")
    return FileResponse(index_path)


@app.post("/api/upload")
async def upload_image(
    file: Annotated[UploadFile, File(...)],
    depth_layers: Annotated[int, Form()] = 6,
    max_studs: Annotated[int, Form()] = 48
) -> JSONResponse:
    """Handles upload, validates size, and processes the image."""
    allowed_types: set[str] = {"image/png", "image/jpeg", "image/webp"}
    content_type: str = file.content_type or ""

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid type. Only PNG, JPEG, and WEBP allowed."
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    # Validate file size by reading to the end, then seeking back
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 5MB."
        )

    # Sanitize filename to prevent path traversal
    safe_name = os.path.basename(file.filename)
    original_path: str = os.path.join(UPLOAD_DIR, safe_name)

    try:
        with open(original_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save error: {e}")

    # Generate Depth Map
    depth_path: str = os.path.join(OUTPUT_DIR, f"depth_{safe_name}")
    try:
        saved_depth = estimate_depth(original_path, depth_path)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Depth error: {e}")

    # Quantize and Map to Colors using user parameters
    try:
        mosaic_data: dict[str, Any] = quantize_image(
            original_path,
            saved_depth,
            PALETTE_PATH,
            depth_layers,
            max_studs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quant failure: {e}")

    return JSONResponse(
        status_code=200,
        content={
            "message": "Processing complete",
            "original": original_path,
            "depth_map": saved_depth,
            "mosaic_data": mosaic_data
        }
    )
