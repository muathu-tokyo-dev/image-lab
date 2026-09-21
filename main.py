from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from algorithms.histogram import apply_histogram
from algorithms.hsv import apply_hsv

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
PREVIEW_MAX_SIDE = 1400
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

app = FastAPI(title="Neon Pixel Image Lab", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class HSVSettings(BaseModel):
    hue: float = Field(0, ge=-180, le=180)
    saturation: float = Field(0, ge=-100, le=100)
    value: float = Field(0, ge=-100, le=100)


class HistogramSettings(BaseModel):
    blacks: float = Field(0, ge=-100, le=100)
    shadows: float = Field(0, ge=-100, le=100)
    midtones: float = Field(0, ge=-100, le=100)
    highlights: float = Field(0, ge=-100, le=100)
    whites: float = Field(0, ge=-100, le=100)


class ProcessRequest(BaseModel):
    image_id: str
    technique: Literal["hsv", "histogram"]
    hsv: HSVSettings = HSVSettings()
    histogram: HistogramSettings = HistogramSettings()


def _safe_image_path(image_id: str) -> Path:
    if not image_id or any(ch not in "0123456789abcdef-" for ch in image_id.lower()):
        raise HTTPException(status_code=400, detail="Invalid image id")
    path = UPLOAD_DIR / f"{image_id}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return path


def _read_bgr(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="Unsupported or corrupt image")
    return image


def _resize_for_preview(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= PREVIEW_MAX_SIDE:
        return image
    scale = PREVIEW_MAX_SIDE / float(longest)
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


def _apply(image: np.ndarray, req: ProcessRequest) -> np.ndarray:
    if req.technique == "hsv":
        return apply_hsv(
            image,
            hue=req.hsv.hue,
            saturation=req.hsv.saturation,
            value=req.hsv.value,
        )
    return apply_histogram(
        image,
        blacks=req.histogram.blacks,
        shadows=req.histogram.shadows,
        midtones=req.histogram.midtones,
        highlights=req.histogram.highlights,
        whites=req.histogram.whites,
    )


def _encode_jpeg(image: np.ndarray, quality: int = 88) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode preview")
    return encoded.tobytes()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Use JPG, PNG, WEBP, or BMP")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum file size is 25 MB")

    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="Unsupported or corrupt image")

    image_id = str(uuid.uuid4())
    target = UPLOAD_DIR / f"{image_id}.png"
    if not cv2.imwrite(str(target), image):
        raise HTTPException(status_code=500, detail="Could not store image")

    return {
        "image_id": image_id,
        "filename": file.filename,
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "original_url": f"/api/original/{image_id}",
    }


@app.get("/api/original/{image_id}")
def original_image(image_id: str):
    image = _resize_for_preview(_read_bgr(_safe_image_path(image_id)))
    return Response(content=_encode_jpeg(image, 90), media_type="image/jpeg")


@app.post("/api/process")
def process_image(req: ProcessRequest):
    image = _resize_for_preview(_read_bgr(_safe_image_path(req.image_id)))
    output = _apply(image, req)
    return StreamingResponse(io.BytesIO(_encode_jpeg(output, 88)), media_type="image/jpeg")


@app.post("/api/export")
def export_image(req: ProcessRequest):
    image = _read_bgr(_safe_image_path(req.image_id))
    output = _apply(image, req)

    export_path = EXPORT_DIR / f"neon-edit-{uuid.uuid4().hex[:8]}.png"
    if not cv2.imwrite(str(export_path), output, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise HTTPException(status_code=500, detail="Could not export image")

    return FileResponse(
        path=export_path,
        media_type="image/png",
        filename=export_path.name,
    )


@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5500,
        reload=True
    )