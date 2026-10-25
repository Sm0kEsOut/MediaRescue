from pathlib import Path
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
import subprocess
import shutil
import warnings
import hashlib
import csv
import sys

def get_ffmpeg_path():
    # Find FFmpeg inside the packaged application.
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent

    bundled = base / "bin" / "ffmpeg.exe"

    if bundled.is_file():
        return str(bundled)

    # When developing, allow installed FFmpeg.
    if not getattr(sys, "frozen", False):
        installed = shutil.which("ffmpeg")
        if installed:
            return installed

    raise FileNotFoundError(
        "FFmpeg was not found. "
        "The application may be missing bundled files."
    )

register_heif_opener()
Image.MAX_IMAGE_PIXELS = 40_000_000

PHOTOS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".bmp", ".gif", ".heic", ".heif", ".avif"
}
VIDEOS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".3gp"}

MAX_PHOTO_BYTES = 100 * 1024 * 1024
MAX_VIDEO_BYTES = 4 * 1024 * 1024 * 1024

def rebuild_photo(src, dest):
    if src.stat().st_size > MAX_PHOTO_BYTES:
        raise ValueError("Photo exceeds size limit")

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)

        with Image.open(src) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Multi-frame image rejected")

            if image.width * image.height > 40_000_000:
                raise ValueError("Image exceeds pixel limit")

            image.load()
            oriented = ImageOps.exif_transpose(image)

            # Reconstruct with pixel data, not original metadata
            if oriented.mode in ("RGBA", "LA", "PA") or (
                "transparency" in oriented.info
            ):
                pixels = oriented.convert("RGBA")
                rebuilt = Image.frombytes(
                    "RGBA", pixels.size, pixels.tobytes()
                )
                output = dest.with_suffix(".png")
                rebuilt.save(output, format="PNG")
            else:
                pixels = oriented.convert("RGB")
                rebuilt = Image.frombytes(
                    "RGB", pixels.size, pixels.tobytes()
                )
                output = dest.with_suffix(".jpg")
                rebuilt.save(output, format="JPEG", quality=95)

    return output

def rebuild_video(src, dest):
    if src.stat().st_size > MAX_VIDEO_BYTES:
        raise ValueError("Video exceeds 4 GB limit")

    output = dest.with_suffix(".mp4")

    command = [
        get_ffmpeg_path(),
        "-hide_banner", "-loglevel", "error",
        "-nostdin", "-n",
        "-i", str(src),
        "-map", "0:V:0",
        "-map", "0:a:0?",
        "-map_metadata", "-1",
        "-map_metadata:s", "-1",
        "-map_chapters", "-1",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=7200
        )

        if result.returncode != 0:
            raise ValueError(result.stderr[-1000:])

        if not output.exists() or output.stat().st_size == 0:
            raise ValueError("No valid output created")

        return output
    except Exception:
        output.unlink(missing_ok=True)
        raise

def process_media(source, target, progress_callback=None):
    source = Path(source).resolve()
    target = Path(target).resolve()

    if not source.is_dir():
        raise ValueError("Originals folder not found")

    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Input and output must be separate")

    photos_dir = target / "Photos"
    videos_dir = target / "Videos"

    photos_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    get_ffmpeg_path()

    results = []

    files = [
        p for p in sorted(source.rglob("*"))
        if p.is_file() and not p.is_symlink()
    ]

    total = len(files)

    for index, path in enumerate(files, start=1):
        if path.is_symlink() or not path.is_file():
            continue

        extension = path.suffix.lower()

        identifier = hashlib.sha256(
            str(path.relative_to(source)).encode("utf-8")
        ).hexdigest()[:20]

        try:
            if extension in PHOTOS:
                output = rebuild_photo(
                    path, photos_dir / identifier
                )
            elif extension in VIDEOS:
                output = rebuild_video(
                    path, videos_dir / identifier
                )
            else:
                print("SKIPPED:", path.name)
                results.append([str(path), "SKIPPED", "Unsupported"])
                if progress_callback:
                    progress_callback(index, total, path.name)
                continue

            print("REBUILT:", path.name)
            results.append([str(path), "REBUILT", str(output)])

        except Exception as e:
            print("REJECTED:", path.name, str(e))
            results.append([str(path), "REJECTED", str(e)])

        if progress_callback:
            progress_callback(index, total, path.name)

    with (target / "report.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Original", "Status", "Details"])
        writer.writerows(results)

    print("\nFinished. Review Clean/report.csv")
    print("REBUILT does not guarantee malware-free.")

def main():
    if len(sys.argv) != 3:
        print(
            'Usage: python media_rescue.py "Originals" "Clean"'
        )
        sys.exit(1)

    process_media(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()