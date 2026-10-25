"""Regression tests for the MediaRescue improved-validation engine.

All media fixtures are generated in temporary folders. No personal media is used.
Run: python -m unittest discover -s tests -v
"""
import csv
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import MediaRescue.media_rescue as mr


class MediaRescueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.target = self.root / 'out'
        self.source.mkdir()

    def image(self, name='photo.png', mode='RGB', size=(32, 24), fmt='PNG'):
        path = self.source / name
        Image.new(mode, size, (20, 80, 160) if mode == 'RGB' else (20, 80, 160, 128)).save(path, format=fmt)
        return path

    def run_engine(self, **kwargs):
        return mr.process_media(self.source, self.target, **kwargs)

    def report_rows(self):
        with (self.target / 'report.csv').open(newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def test_valid_png_is_rebuilt(self):
        self.image()
        result = self.run_engine()
        self.assertEqual(result['counts']['REBUILT'], 1)
        self.assertFalse(result['cancelled'])
        outputs = list((self.target / 'Photos').glob('*.jpg'))
        self.assertEqual(len(outputs), 1)
        with Image.open(outputs[0]) as img:
            self.assertEqual(img.format, 'JPEG')
            self.assertEqual(img.size, (32, 24))
        self.assertEqual(self.report_rows()[0]['Status'], 'REBUILT')

    def test_transparency_retained_without_original_metadata(self):
        path = self.image(name='alpha.png', mode='RGBA')
        # Separate metadata input from pixels; output should have no original text metadata.
        from PIL import PngImagePlugin
        info = PngImagePlugin.PngInfo()
        info.add_text('comment', 'private fixture metadata')
        Image.new('RGBA', (32, 24), (20, 80, 160, 128)).save(path, pnginfo=info)
        self.run_engine()
        output = next((self.target / 'Photos').glob('*.png'))
        with Image.open(output) as img:
            self.assertEqual(img.mode, 'RGBA')
            self.assertEqual(img.getpixel((0, 0))[3], 128)
            self.assertNotIn('comment', img.info)

    def test_extension_format_mismatch_rejected(self):
        self.image(name='disguised.jpg', fmt='PNG')
        result = self.run_engine()
        self.assertEqual(result['counts']['REJECTED'], 1)
        self.assertIn('does not match extension', self.report_rows()[0]['Details'])
        self.assertEqual(list((self.target / 'Photos').iterdir()), [])

    def test_broken_image_rejected(self):
        (self.source / 'corrupt.png').write_bytes(b'not a valid png')
        result = self.run_engine()
        self.assertEqual(result['counts']['REJECTED'], 1)
        self.assertEqual(self.report_rows()[0]['Status'], 'REJECTED')

    def test_empty_photo_rejected(self):
        (self.source / 'empty.jpg').touch()
        self.assertEqual(self.run_engine()['counts']['REJECTED'], 1)

    def test_multi_frame_gif_rejected(self):
        path = self.source / 'animated.gif'
        a = Image.new('RGB', (16, 16), 'red')
        b = Image.new('RGB', (16, 16), 'blue')
        a.save(path, save_all=True, append_images=[b], duration=100, loop=0)
        self.assertEqual(self.run_engine()['counts']['REJECTED'], 1)
        self.assertIn('Multi-frame', self.report_rows()[0]['Details'])

    def test_large_pixel_count_rejected_without_large_fixture(self):
        self.image()
        with patch.object(mr.Image, 'MAX_IMAGE_PIXELS', 100):
            result = self.run_engine()
        self.assertEqual(result['counts']['REJECTED'], 1)

    def test_unsupported_file_skipped(self):
        (self.source / 'sample.exe').write_bytes(b'dummy')
        result = self.run_engine()
        self.assertEqual(result['counts']['SKIPPED'], 1)
        self.assertEqual(self.report_rows()[0]['Status'], 'SKIPPED')

    def test_symlink_not_processed(self):
        self.image()
        link = self.source / 'shortcut.png'
        try:
            link.symlink_to(self.source / 'photo.png')
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks unavailable without privileges')
        result = self.run_engine()
        self.assertEqual(result['total'], 1)

    def test_callback_reports_status(self):
        self.image()
        (self.source / 'notes.txt').write_text('hello')
        updates = []
        result = self.run_engine(progress_callback=lambda *args: updates.append(args))
        self.assertEqual(result['processed'], 2)
        self.assertEqual(len(updates), 2)
        self.assertEqual({event[3] for event in updates}, {'REBUILT', 'SKIPPED'})
        self.assertEqual(updates[-1][0], 2)

    def test_cancellation_preserves_report(self):
        self.image('a.png')
        self.image('b.png')
        stop = threading.Event()
        def callback(done, total, filename, status):
            stop.set()
        result = self.run_engine(progress_callback=callback, cancel_event=stop)
        self.assertTrue(result['cancelled'])
        self.assertEqual(result['processed'], 1)
        self.assertEqual(len(self.report_rows()), 1)

    def test_nested_target_rejected(self):
        self.image()
        with self.assertRaises(ValueError):
            mr.process_media(self.source, self.source / 'out')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'FFmpeg and FFprobe required for video integration tests')
    def test_valid_video_rebuilt(self):
        video = self.source / 'clip.mp4'
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'lavfi', '-i', 'color=c=blue:s=64x48:r=10:d=1',
            '-c:v', 'mpeg4', '-pix_fmt', 'yuv420p', str(video)
        ], check=True, timeout=30)
        result = self.run_engine()
        self.assertEqual(result['counts']['REBUILT'], 1, self.report_rows())
        output = next((self.target / 'Videos').glob('*.mp4'))
        self.assertGreater(output.stat().st_size, 0)
        self.assertEqual(self.report_rows()[0]['Status'], 'REBUILT')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'FFmpeg and FFprobe required for video integration tests')
    def test_fake_mp4_rejected(self):
        (self.source / 'fake.mp4').write_bytes(b'not a video')
        result = self.run_engine()
        self.assertEqual(result['counts']['REJECTED'], 1)
        self.assertEqual(self.report_rows()[0]['Status'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
