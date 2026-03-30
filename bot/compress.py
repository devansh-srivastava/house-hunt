"""
Media compression helpers — shrink images and videos before upload.
Images: Pillow resize + quality reduction.
Videos: ffmpeg transcode to H.264 720p.
"""
import io
import logging
import shutil
import subprocess
import tempfile
import os

from PIL import Image

logger = logging.getLogger(__name__)

# ── Limits ──
MAX_IMAGE_SIDE = 1920        # longest edge in pixels
IMAGE_QUALITY_START = 82     # JPEG quality to try first
IMAGE_QUALITY_MIN = 60       # lowest quality we'll go
IMAGE_TARGET_BYTES = 1_000_000  # 1 MB target for images
SKIP_IF_UNDER_BYTES = 500_000   # don't compress files already under 500 KB

VIDEO_CRF = "28"             # H.264 quality (lower = better, 23 is default)
VIDEO_MAX_WIDTH = 1280       # scale down to 720p-ish
VIDEO_AUDIO_BITRATE = "96k"


# ── Image Compression ──

def compress_image(data: bytes) -> tuple[bytes, str]:
    """
    Compress an image: resize to max 1920px, save as JPEG with decreasing quality
    until it fits under the target size.
    Returns (compressed_bytes, content_type).
    """
    original_size = len(data)

    # Small files — skip compression entirely
    if original_size <= SKIP_IF_UNDER_BYTES:
        logger.info("[COMPRESS] Image already small (%d KB), skipping", original_size // 1024)
        return data, "image/jpeg"

    img = Image.open(io.BytesIO(data))

    # Convert to RGB if needed (strips alpha channel for JPEG)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # Resize if either side exceeds the max
    w, h = img.size
    if max(w, h) > MAX_IMAGE_SIDE:
        ratio = MAX_IMAGE_SIDE / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.info("[COMPRESS] Resized image %dx%d → %dx%d", w, h, new_w, new_h)

    # Try decreasing quality until we hit the target size
    quality = IMAGE_QUALITY_START
    while quality >= IMAGE_QUALITY_MIN:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        compressed = buf.getvalue()

        if len(compressed) <= IMAGE_TARGET_BYTES:
            break  # good enough
        quality -= 5  # step down and try again

    # If compressed is somehow bigger than original, keep original
    if len(compressed) >= original_size:
        logger.info("[COMPRESS] Compression didn't help, keeping original (%d KB)", original_size // 1024)
        return data, "image/jpeg"

    pct = round((1 - len(compressed) / original_size) * 100)
    logger.info(
        "[COMPRESS] Image: %d KB → %d KB (-%d%%, quality=%d)",
        original_size // 1024, len(compressed) // 1024, pct, quality,
    )
    return compressed, "image/jpeg"


# ── Video Compression ──

def _ffmpeg_available() -> bool:
    """Check if ffmpeg is installed and accessible."""
    return shutil.which("ffmpeg") is not None


def compress_video(data: bytes) -> tuple[bytes, str]:
    """
    Compress a video using ffmpeg: H.264 + AAC, max 1280px wide, CRF 28.
    Returns (compressed_bytes, content_type).
    Falls back to original if ffmpeg is missing or compression fails.
    """
    original_size = len(data)

    # Small files — skip
    if original_size <= SKIP_IF_UNDER_BYTES:
        logger.info("[COMPRESS] Video already small (%d KB), skipping", original_size // 1024)
        return data, "video/mp4"

    if not _ffmpeg_available():
        logger.warning("[COMPRESS] ffmpeg not found, skipping video compression")
        return data, "video/mp4"

    # Write input to a temp file, run ffmpeg, read output
    tmp_dir = tempfile.mkdtemp(prefix="hh_vid_")
    in_path = os.path.join(tmp_dir, "input.mp4")
    out_path = os.path.join(tmp_dir, "output.mp4")

    try:
        with open(in_path, "wb") as f:
            f.write(data)

        # ffmpeg command:
        #   -i input  -vf scale (cap width at 1280, keep aspect)
        #   -c:v libx264 -crf 28  -c:a aac -b:a 96k
        #   -movflags +faststart  (puts metadata at start for streaming)
        #   -y (overwrite output)
        cmd = [
            "ffmpeg", "-i", in_path,
            "-vf", f"scale='min({VIDEO_MAX_WIDTH},iw)':-2",
            "-c:v", "libx264", "-crf", VIDEO_CRF, "-preset", "fast",
            "-c:a", "aac", "-b:a", VIDEO_AUDIO_BITRATE,
            "-movflags", "+faststart",
            "-y", out_path,
        ]

        result = subprocess.run(
            cmd, capture_output=True, timeout=120,  # 2-minute safety cap
        )

        if result.returncode != 0:
            logger.error("[COMPRESS] ffmpeg failed: %s", result.stderr[-500:])
            return data, "video/mp4"

        with open(out_path, "rb") as f:
            compressed = f.read()

        # If output is bigger, keep original
        if len(compressed) >= original_size:
            logger.info("[COMPRESS] Video compression didn't help, keeping original")
            return data, "video/mp4"

        pct = round((1 - len(compressed) / original_size) * 100)
        logger.info(
            "[COMPRESS] Video: %d KB → %d KB (-%d%%)",
            original_size // 1024, len(compressed) // 1024, pct,
        )
        return compressed, "video/mp4"

    except subprocess.TimeoutExpired:
        logger.warning("[COMPRESS] ffmpeg timed out, keeping original video")
        return data, "video/mp4"
    except Exception as exc:
        logger.error("[COMPRESS] Video compression error: %s", exc)
        return data, "video/mp4"
    finally:
        # Clean up temp files
        for p in (in_path, out_path):
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)
