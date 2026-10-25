from pathlib import Path
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
import subprocess
import shutil
import warnings
import hashlib
import csv
import sys
import os
import stat
import time
import json
import math
from reporting import write_html_report

register_heif_opener()
Image.MAX_IMAGE_PIXELS = 40_000_000

PHOTOS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.heic', '.heif', '.avif'}
VIDEOS = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp'}
MAX_PHOTO_BYTES = 100 * 1024 * 1024
MAX_VIDEO_BYTES = 4 * 1024 * 1024 * 1024
MAX_VIDEO_SECONDS = 2 * 60 * 60
MAX_VIDEO_PIXELS = 3840 * 2160
IMAGE_FORMATS = {
    '.jpg': {'JPEG'}, '.jpeg': {'JPEG'}, '.png': {'PNG'},
    '.webp': {'WEBP'}, '.bmp': {'BMP'}, '.gif': {'GIF'},
    '.heic': {'HEIF'}, '.heif': {'HEIF'}, '.avif': {'AVIF'}
}
# ffprobe's format_name may include aliases separated by commas.
VIDEO_FORMATS = {
    '.mp4': {'mov', 'mp4', 'm4a', '3gp', '3g2', 'mj2'},
    '.mov': {'mov', 'mp4', 'm4a', '3gp', '3g2', 'mj2'},
    '.m4v': {'mov', 'mp4', 'm4a', '3gp', '3g2', 'mj2'},
    '.3gp': {'mov', 'mp4', 'm4a', '3gp', '3g2', 'mj2'},
    '.avi': {'avi'}, '.mkv': {'matroska', 'webm'},
    '.webm': {'matroska', 'webm'},
}


class Cancelled(Exception):
    """Raised when the user cancels reconstruction."""


def ffmpeg_path():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    bundled = base / 'bin' / 'ffmpeg.exe'
    if bundled.is_file():
        return str(bundled)
    executable = shutil.which('ffmpeg')
    if executable:
        return executable
    raise FileNotFoundError('FFmpeg not found (bundle bin/ffmpeg.exe or install FFmpeg).')


def ffprobe_path():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    bundled = base / 'bin' / 'ffprobe.exe'
    if bundled.is_file():
        return str(bundled)
    found = shutil.which('ffprobe')
    if found:
        return found
    raise FileNotFoundError('FFprobe missing: bundle bin/ffprobe.exe with FFmpeg.')


def validate_video(src, cancel_event):
    """Preflight metadata check, NOT a full malware or decode scan."""
    if cancel_event.is_set():
        raise Cancelled()
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    cmd = [ffprobe_path(), '-v', 'error', '-show_entries',
           'format=format_name,duration:stream=codec_type,width,height',
           '-of', 'json', str(src)]
    try:
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=30,
                                creationflags=flags)
    except subprocess.TimeoutExpired:
        raise ValueError('Video metadata probe timed out')
    if result.returncode != 0:
        raise ValueError('Video metadata could not be read')
    try:
        data = json.loads(result.stdout)
        fmt = data['format']['format_name']
        accepted = VIDEO_FORMATS[src.suffix.lower()]
        if not (set(fmt.split(',')) & accepted):
            raise ValueError('Video container does not match extension')
        duration = float(data['format']['duration'])
        if not math.isfinite(duration) or not 0 < duration <= MAX_VIDEO_SECONDS:
            raise ValueError('Video duration missing, invalid, or exceeds 2 hours')
        streams = data.get('streams', [])
        vids = [x for x in streams if x.get('codec_type') == 'video']
        if len(vids) != 1:
            raise ValueError('Expected exactly one video stream')
        width, height = int(vids[0]['width']), int(vids[0]['height'])
        if not (0 < width <= 3840 and 0 < height <= 3840 and
                width * height <= MAX_VIDEO_PIXELS):
            raise ValueError('Video resolution exceeds limit')
    except (KeyError, TypeError, OverflowError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError('Invalid or missing video metadata') from exc
    if cancel_event.is_set():
        raise Cancelled()


def is_reparse_point(path):
    try:
        info = path.lstat()
        return path.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))
    except OSError:
        return True


def enumerate_files(source):
    """Avoid traversing Windows junctions and symlinked directories."""
    found = []
    for root, dirs, files in os.walk(source, followlinks=False):
        root_path = Path(root)
        dirs[:] = sorted(d for d in dirs if not is_reparse_point(root_path / d))
        for filename in sorted(files):
            path = root_path / filename
            if not is_reparse_point(path) and path.is_file():
                found.append(path)
    return found


def rebuild_photo(src, dest, cancel_event):
    if cancel_event.is_set():
        raise Cancelled()
    if not 0 < src.stat().st_size <= MAX_PHOTO_BYTES:
        raise ValueError('Photo is empty or exceeds 100 MB limit')

    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(src, formats=list(set().union(*IMAGE_FORMATS.values()))) as image:
            if image.format not in IMAGE_FORMATS[src.suffix.lower()]:
                raise ValueError('Image format does not match extension')
            if getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Multi-frame image rejected')
            if image.width * image.height > Image.MAX_IMAGE_PIXELS:
                raise ValueError('Image exceeds pixel limit')
            image.load()
            if cancel_event.is_set():
                raise Cancelled()
            oriented = ImageOps.exif_transpose(image)
            has_alpha = oriented.mode in ('RGBA', 'LA', 'PA') or 'transparency' in oriented.info
            mode = 'RGBA' if has_alpha else 'RGB'
            pixels = oriented.convert(mode)
            rebuilt = Image.frombytes(mode, pixels.size, pixels.tobytes())
            output = dest.with_suffix('.png' if has_alpha else '.jpg')
            temp = dest.with_suffix('.part')
            try:
                if has_alpha:
                    rebuilt.save(temp, format='PNG')
                else:
                    rebuilt.save(temp, format='JPEG', quality=95)
                if cancel_event.is_set():
                    raise Cancelled()
                temp.replace(output)
                return output
            finally:
                temp.unlink(missing_ok=True)


def rebuild_video(src, dest, cancel_event):
    if cancel_event.is_set():
        raise Cancelled()
    if not 0 < src.stat().st_size <= MAX_VIDEO_BYTES:
        raise ValueError('Video is empty or exceeds 4 GB limit')
    validate_video(src, cancel_event)
    output = dest.with_suffix('.mp4')
    temp = dest.with_suffix('.part.mp4')
    cmd = [
        ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
        '-i', str(src), '-map', '0:V:0', '-map', '0:a:0?',
        '-map_metadata', '-1', '-map_metadata:s', '-1', '-map_chapters', '-1',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(temp)
    ]
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    proc = None
    try:
        # Avoid PIPE deadlocks by sending FFmpeg diagnostics to a temporary file.
        from tempfile import TemporaryFile
        with TemporaryFile(mode='w+t', encoding='utf-8', errors='replace') as errors:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=errors, creationflags=flags)
            deadline = time.monotonic() + 7200
            while proc.poll() is None:
                if cancel_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    raise Cancelled()
                if time.monotonic() > deadline:
                    proc.kill()
                    proc.wait()
                    raise TimeoutError('Video encoding exceeded the 2-hour limit')
                cancel_event.wait(0.25)
            if proc.returncode != 0:
                errors.seek(0)
                raise ValueError('FFmpeg failed: ' + errors.read()[-1000:])
        if cancel_event.is_set():
            raise Cancelled()
        if not temp.is_file() or temp.stat().st_size == 0:
            raise ValueError('No output created')
        temp.replace(output)
        return output
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
        temp.unlink(missing_ok=True)


def process_media(source, target, progress_callback=None, cancel_event=None):
    """progress_callback(done, total, filename, status); returns summary dict."""
    if cancel_event is None:
        from threading import Event
        cancel_event = Event()
    source = Path(source).resolve()
    target = Path(target).resolve()
    if not source.is_dir():
        raise ValueError('Source folder not found')
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('Input and output must be separate non-nested folders')
    # Fail early if video processing is requested and FFmpeg is unavailable.
    files = enumerate_files(source)
    if any(p.suffix.lower() in VIDEOS for p in files):
        ffmpeg_path()
        ffprobe_path()
    photos_dir = target / 'Photos'
    videos_dir = target / 'Videos'
    photos_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)
    results = []
    totals = {'REBUILT': 0, 'REJECTED': 0, 'SKIPPED': 0}
    was_cancelled = False
    try:
        for index, path in enumerate(files, 1):
            if cancel_event.is_set():
                was_cancelled = True
                break
            ext = path.suffix.lower()
            identifier = hashlib.sha256(str(path.relative_to(source)).encode('utf-8')).hexdigest()[:20]
            status = 'SKIPPED'
            detail = 'Unsupported extension'
            try:
                if is_reparse_point(path) or not path.is_file():
                    raise ValueError('Unsafe or missing file path')
                if ext in PHOTOS:
                    output = rebuild_photo(path, photos_dir / identifier, cancel_event)
                elif ext in VIDEOS:
                    output = rebuild_video(path, videos_dir / identifier, cancel_event)
                else:
                    output = None
                if output is not None:
                    status = 'REBUILT'
                    detail = str(output)
            except Cancelled:
                was_cancelled = True
                break
            except Exception as exc:
                status = 'REJECTED'
                detail = str(exc)
            totals[status] += 1
            results.append([str(path), status, detail])
            if progress_callback:
                progress_callback(index, len(files), path.name, status)
    finally:
        with (target / 'report.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Original', 'Status', 'Details'])
            writer.writerows(results)
        write_html_report(target / 'report.html', results, total=len(files), cancelled=was_cancelled)
    return {'total': len(files), 'processed': len(results), 'counts': totals,
            'cancelled': was_cancelled, 'report': str(target / 'report.csv'), 'html_report': str(target / 'report.html')}


def main():
    if len(sys.argv) != 3:
        sys.exit('Usage: python media_rescue.py "Originals" "Clean"')
    def progress(done, total, name, status):
        print(f'[{done}/{total}] {status}: {name}', flush=True)
    from threading import Event
    try:
        summary = process_media(sys.argv[1], sys.argv[2], progress, Event())
        print(summary)
    except Exception as exc:
        sys.exit(f'Error: {exc}')


if __name__ == '__main__':
    main()
