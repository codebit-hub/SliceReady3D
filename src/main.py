import os
from typing import Annotated

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import our new depth estimation logic
from src.depth_pipeline import estimate_depth

# Load environment variables from the .env file
load_dotenv()

app = FastAPI(title="SliceReady3D API")

UPLOAD_DIR = "src/uploads"
# Create a dedicated directory for our generated depth maps
OUTPUT_DIR = "src/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.post("/api/upload")
async def upload_image(
    file: Annotated[UploadFile, File(...)],
) -> JSONResponse:
    """
    Handles image upload, saves it, and immediately triggers
    the depth estimation pipeline.
    """
    allowed_types: set[str] = {"image/png", "image/jpeg", "image/webp"}
    content_type: str = file.content_type or ""

    if content_type not in allowed_types:
        error_msg = (
            f"Invalid file type: {content_type}. "
            "Only PNG, JPEG, and WEBP are allowed."
        )
        raise HTTPException(status_code=400, detail=error_msg)

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing from the upload."
        )

    # Step 1: Save the original file
    original_path: str = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(original_path, "wb") as buffer:
            content: bytes = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while saving: {str(e)}"
        )

    # Step 2: Define where the resulting depth map will be saved
    depth_filename = f"depth_{file.filename}"
    depth_path: str = os.path.join(OUTPUT_DIR, depth_filename)

    # Step 3: Trigger the depth estimation pipeline
    try:
        saved_depth_path = estimate_depth(original_path, depth_path)
    except HTTPException as he:
        # Re-raise HTTP exceptions from the pipeline so FastAPI handles them
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Depth pipeline failed: {str(e)}"
        )

    # Step 4: Return success with paths to both images
    return JSONResponse(
        status_code=200,
        content={
            "message": "Pipeline processed successfully",
            "original_image": original_path,
            "depth_map": saved_depth_path
        }
    )
