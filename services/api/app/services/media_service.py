"""Media service for image validation, processing, and S3/MinIO uploads."""

import io
import os
import uuid

import boto3
import structlog
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import get_settings

logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Variant definitions: name -> (max_width, max_height, mode)
# mode: "cover" = thumbnail with crop, "inside" = thumbnail preserving aspect within bounds
VARIANTS = {
    "thumbnail": (400, 300, "cover"),
    "web": (1200, 800, "inside"),
    "og": (1200, 630, "cover"),
    "instagram": (1080, 1080, "cover"),
}


def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=boto3.session.Config(
            signature_version=settings.s3_signature_version,
        ),
    )


def _sniff_image_extension(file_bytes: bytes, filename: str | None, content_type: str | None) -> str:
    """Resolve extension from filename, Content-Type, or magic bytes (PNG/JPEG/WebP)."""
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            return ext
        # Windows sometimes sends "file.PNG"
        if ext.upper() in {e.upper() for e in ALLOWED_EXTENSIONS}:
            return ext.lower()

    ct = (content_type or "").split(";")[0].strip().lower()
    by_ct = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
    }
    if ct in by_ct:
        return by_ct[ct]

    # Magic bytes
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if file_bytes[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return ".webp"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Unsupported or missing image type "
            f"(filename={filename!r}, content_type={content_type!r}). "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        ),
    )


async def validate_image(file: UploadFile) -> tuple[bytes, int, int, str, str]:
    """Validate an uploaded image file.

    Returns (file_bytes, width, height, mime_type, extension).
    Raises HTTPException on validation failure.
    """
    # Read first — needed for magic-byte detection when filename is odd
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if file.content_type and not (
        file.content_type.startswith("image/")
        or file.content_type in ("application/octet-stream", "binary/octet-stream")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only image files are supported (got {file.content_type})",
        )

    ext = _sniff_image_extension(file_bytes, file.filename, file.content_type)

    # Validate with Pillow
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()  # force decode (better than verify() for some PNGs)
        width, height = img.size
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unsupported image: {str(e)}",
        ) from e

    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(ext, file.content_type or f"image/{ext.lstrip('.')}")
    if ext == ".jpeg":
        ext = ".jpg"
        mime_type = "image/jpeg"

    return file_bytes, width, height, mime_type, ext


async def process_and_upload_image(
    file_bytes: bytes,
    listing_id: uuid.UUID,
    media_id: uuid.UUID,
    original_name: str,
) -> dict:
    """Process and upload image variants to S3.

    Returns a dict: {
        "width": int,
        "height": int,
        "variants": {"thumbnail": "object_key", "web": "object_key", ...},
        "original_object_key": str,
        "size_bytes": int,
        "mime_type": str,
    }
    """
    import asyncio

    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"

    # Determine output format - use WebP when input is WebP, otherwise JPEG
    output_format = "WebP" if ext == ".webp" else "JPEG"
    output_ext = ".webp" if ext == ".webp" else ".jpg"
    save_kwargs = {"quality": 85}
    if output_format == "WebP":
        save_kwargs["quality"] = 80

    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Convert RGBA to RGB for JPEG
        if output_format == "JPEG" and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process image: {str(e)}",
        ) from e

    width, height = img.size

    s3_client = get_s3_client()
    settings = get_settings()
    bucket = settings.s3_bucket_name

    base_prefix = f"listings/{listing_id}/{media_id}"

    # Upload original
    original_key = f"{base_prefix}/original{ext}"
    original_buffer = io.BytesIO(file_bytes)
    await asyncio.to_thread(
        s3_client.upload_fileobj,
        original_buffer,
        bucket,
        original_key,
    )

    variants: dict[str, str] = {}

    for variant_name, (max_w, max_h, mode) in VARIANTS.items():
        variant_img = img.copy()

        if mode == "cover":
            # Crop to target aspect ratio then resize
            target_ratio = max_w / max_h
            img_ratio = width / height
            if img_ratio > target_ratio:
                # Image is wider than target: crop width
                new_width = int(height * target_ratio)
                left = (width - new_width) // 2
                variant_img = variant_img.crop((left, 0, left + new_width, height))
            else:
                # Image is taller than target: crop height
                new_height = int(width / target_ratio)
                top = (height - new_height) // 2
                variant_img = variant_img.crop((0, top, width, top + new_height))
            variant_img.thumbnail((max_w, max_h), Image.LANCZOS)
        else:
            # "inside" mode: fit within bounds preserving aspect
            variant_img.thumbnail((max_w, max_h), Image.LANCZOS)

        variant_key = f"{base_prefix}/{variant_name}{output_ext}"
        variant_buffer = io.BytesIO()
        if output_format == "WebP":
            variant_img.save(variant_buffer, format="WebP", quality=save_kwargs["quality"])
        else:
            variant_img.save(variant_buffer, format="JPEG", quality=save_kwargs["quality"])
        variant_buffer.seek(0)

        await asyncio.to_thread(
            s3_client.upload_fileobj,
            variant_buffer,
            bucket,
            variant_key,
        )
        variants[variant_name] = variant_key

    return {
        "width": width,
        "height": height,
        "variants": variants,
        "original_object_key": original_key,
        "size_bytes": len(file_bytes),
        "mime_type": f"image/{output_ext.lstrip('.')}",
    }


async def get_presigned_url(object_key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL for reading an S3 object."""
    import asyncio

    s3_client = get_s3_client()
    settings = get_settings()

    url = await asyncio.to_thread(
        s3_client.generate_presigned_url,
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": object_key},
        ExpiresIn=expiration,
    )
    return url


async def delete_objects(object_keys: list[str]) -> None:
    """Delete multiple objects from S3."""
    import asyncio

    if not object_keys:
        return

    s3_client = get_s3_client()
    settings = get_settings()

    for key in object_keys:
        try:
            await asyncio.to_thread(
                s3_client.delete_object,
                Bucket=settings.s3_bucket_name,
                Key=key,
            )
        except Exception as e:
            logger.warning("s3_delete_warning", key=key, error=str(e))


def _to_rgb_flat(img: Image.Image) -> Image.Image:
    """Convert any mode to RGB (flatten alpha onto white)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def fit_instagram_feed_image(img: Image.Image, size: int = 1080) -> Image.Image:
    """Crop/pad to an Instagram-safe aspect ratio for feed posts.

    Instagram Graph requires aspect ratio between **4:5 (0.8)** and **1.91:1**.
    We produce a **1:1 square** (always valid) via center-cover crop to ``size x size``.
    """
    img = _to_rgb_flat(img)
    w, h = img.size
    if w <= 0 or h <= 0:
        return Image.new("RGB", (size, size), (255, 255, 255))

    # Center cover crop to square
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    square = img.crop((left, top, left + side, top + side))
    if square.size != (size, size):
        square = square.resize((size, size), Image.Resampling.LANCZOS)
    return square


async def upload_library_image(
    file_bytes: bytes,
    org_id: uuid.UUID,
    media_id: uuid.UUID,
    ext: str,
    mime_type: str,
) -> tuple[str, str, int]:
    """Upload a library image; return (object_key, public_url, size_bytes).

    Always converts to **1080×1080 JPEG** so Instagram accepts the aspect ratio.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
        variant = fit_instagram_feed_image(img, size=1080)
        buf = io.BytesIO()
        variant.save(buf, format="JPEG", quality=90, optimize=True)
        upload_bytes = buf.getvalue()
        upload_ext = ".jpg"
        mime_type = "image/jpeg"
        logger.info(
            "library_image_instagram_fit",
            org_id=str(org_id),
            media_id=str(media_id),
            out_bytes=len(upload_bytes),
        )
    except Exception as exc:
        logger.warning("library_image_convert_failed", error=str(exc), ext=ext)
        # Last resort: try square again on a blank failure path is worse —
        # upload original only if we truly cannot convert
        upload_bytes = file_bytes
        upload_ext = ext if ext in ALLOWED_EXTENSIONS else ".jpg"

    return await upload_library_bytes(
        file_bytes=upload_bytes,
        org_id=org_id,
        media_id=media_id,
        ext=upload_ext,
        mime_type=mime_type,
        subfolder="image",
    )


async def upload_library_bytes(
    file_bytes: bytes,
    org_id: uuid.UUID,
    media_id: uuid.UUID,
    ext: str,
    mime_type: str,
    subfolder: str = "file",
) -> tuple[str, str, int]:
    """Upload raw bytes to org media library path; return (key, public_url, size)."""
    import asyncio

    s3_client = get_s3_client()
    settings = get_settings()
    bucket = settings.s3_bucket_name
    key = f"library/{org_id}/{subfolder}/{media_id}{ext}"
    buffer = io.BytesIO(file_bytes)

    def _upload() -> None:
        kwargs: dict = {}
        if mime_type:
            kwargs["ExtraArgs"] = {"ContentType": mime_type}
        s3_client.upload_fileobj(buffer, bucket, key, **kwargs)

    await asyncio.to_thread(_upload)
    base = (settings.s3_public_url or "").rstrip("/")
    public_url = f"{base}/{key.lstrip('/')}" if base else key
    return key, public_url, len(file_bytes)
