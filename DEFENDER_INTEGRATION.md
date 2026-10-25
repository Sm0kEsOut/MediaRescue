# Optional Microsoft Defender integration

This update is based on the MediaRescue improved-validation edition. It adds `defender_scan.py` and an opt-in checkbox in `gui.py`; the existing `media_rescue.py` engine is otherwise unchanged.

## Setup

Place `gui.py`, `media_rescue.py`, and `defender_scan.py` together in the repository root. Preserve `bin/ffmpeg.exe` and `bin/ffprobe.exe` from your existing setup. No new Python pip dependencies are needed.

The optional Defender checkbox is **off by default**. When selected, MediaRescue scans the original input folder before processing. If Defender returns nonzero, the operation stops. After a completed reconstruction with at least one rebuilt file, it scans the output folder. A final scan error is shown as failure; it does not delete completed files. Check Windows Security > Protection history for detections.

It uses Microsoft's `MpCmdRun.exe -Scan -ScanType 3 -File <folder> -DisableRemediation`. The `-DisableRemediation` switch avoids auto-quarantine/remediation by this explicit scan; Defender's normal real-time protection is not disabled. This option also ignores configured AV exclusions in the custom scan. Review Defender's documentation and your organization's security policy before use. Exit-code 0 and no reported detection do not prove that files are safe; scan results are not Pegasus detection.

If Defender is missing, unavailable, or returns an error, the optional scan fails closed. If you press Cancel, the app terminates the invoked scan process; Windows Defender background services may continue working independently.

## Build with PyInstaller (PowerShell)

```powershell
python -m PyInstaller --onedir --windowed --clean --noconfirm --noupx --name MediaRescue --collect-all PIL --collect-all pillow_heif --add-binary "bin\ffmpeg.exe;bin" --add-binary "bin\ffprobe.exe;bin" gui.py
```

PyInstaller discovers `defender_scan.py` through its import in `gui.py`. Do not bundle Defender binaries: they are part of Windows. Test on Windows 11 with the checkbox **off** and **on**, including a scan error/cancel case, before releasing.

## Security limitations

The scan may fail if Microsoft Defender is disabled, not installed, or restricted by device policy. The Windows Defender scan can quarantine or block files via other real-time protection features, even though this explicit scan requests no remediation. The program cannot establish that files are free from Pegasus, zero-days, or malware. Run untrusted media conversions in an isolated environment where practical.
