# MediaRescue automated tests

This update adds `tests/test_media_rescue.py` and `.github/workflows/tests.yml`.

## How to install

1. Extract this ZIP.
2. Copy `tests/` and `.github/` into the root of your **existing** MediaRescue GitHub project, beside `media_rescue.py` and `requirements.txt`.
3. Do not replace your existing media processing files. These tests target the improved-validation version of `media_rescue.py` (with `process_media`, `cancel_event`, and `progress_callback`).

## Running tests in Windows PowerShell

```powershell
python -m pip install -r requirements.txt
ffmpeg -version
ffprobe -version
python -m unittest discover -s tests -v
```

The tests create temporary, harmless test images and synthetic videos; they never use your personal photos. They exercise successful conversions, file extension mismatch, corrupt/empty files, animated GIF rejection, metadata stripping, size limits, symlink handling, skip behavior, progress callbacks, and cancellation/report preservation. Video tests are automatically skipped if FFmpeg and FFprobe are unavailable.

`OK` means all tests that actually ran passed. `skipped` means those cases were not tested. Run the suite again with both executables installed so video conversion is tested.

## GitHub Actions

Once committed and pushed, the Tests workflow runs on pushes and pull requests using a Windows hosted runner. Check the **Actions** tab to see green/red results. The workflow installs Python dependencies and FFmpeg separately. If Chocolatey installation changes on hosted runners, adjust the workflow accordingly.

## Security limitations

Passing tests means the tested behavior works. It does **not** establish protection against malicious media or all vulnerabilities. In particular, do not execute untrusted samples directly on your usual computer. Use a restricted VM for hostile-file fuzzing and testing.

## Future improvements

- Add tests for HEIC/AVIF when supported fixtures are available.
- Add FFprobe mocking for timeout and unusual metadata edge cases.
- Add property-based fuzzing in a disposable environment.
- Have the CI system build PyInstaller artifacts after tests pass.
