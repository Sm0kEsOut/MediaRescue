# MediaRescue

**A local Windows photo and video reconstruction utility.** MediaRescue decodes supported media and writes new JPEG/PNG images or H.264/AAC MP4 videos. It is intended to help reduce the original file structures and metadata transferred between devices.

> **Security warning:** MediaRescue is **not** antivirus software or a Pegasus detector. A successful rebuild or Microsoft Defender scan does **not** prove a file is malware-free. Parsing untrusted media may expose vulnerabilities in Pillow, pillow-heif, FFmpeg, or FFprobe. For high-risk sources, work in an isolated, updated virtual machine.

## Features

- Windows desktop GUI with input and output folder pickers
- Photo rebuilds (JPEG, PNG, WebP, BMP, single-frame GIF, HEIC/HEIF, AVIF where supported)
- Video re-encoding (MP4, MOV, M4V, AVI, MKV, WebM, 3GP where supported)
- File-format and video-stream validation, plus size, duration and resolution limits
- Progress bar, cancellation during video processing, and per-file statuses
- **Optional** Microsoft Defender scan of original and output folders; scan errors or detections are not treated as clearance
- **Two reports:** `report.csv` for machines and `report.html` for humans
- Original files are left unchanged; unsupported or rejected files are not copied into the rebuilt media folders

## Download and use on Windows

If a tested build is available under [GitHub Releases](../../releases), download the complete Windows ZIP, extract the full folder, and launch `MediaRescue.exe`. Do not move the `.exe` out of the extracted application folder. The standalone build should bundle Python libraries and FFmpeg/FFprobe; verify this in that release's notes.

1. Update Windows and scan downloaded files with your normal antivirus.
2. Run MediaRescue. Choose separate **Source** and **Output** folders (neither should be inside the other).
3. Optionally check **Scan originals and output with Microsoft Defender**.
4. Select **Start Reconstruction**. You can cancel; the report will show how many files were processed.
5. Open **HTML Report** to see rebuilt, rejected, skipped and unprocessed counts, with file-by-file details.
6. Inspect the output and antivirus status before transferring only rebuilt files.

**Important:** The report describes **reconstruction**, not a malware clearance. Defender scan messages appear in the GUI log and Windows Security's history, not as a pass/fail verdict in the HTML report. Do not upload private reports to public GitHub issues: reports may include personal file paths and filenames.

## Run from source

Requirements: Windows 11, supported Python 3, FFmpeg and FFprobe on PATH or in `bin/`, and Python packages from `requirements.txt`.

```powershell
python -m pip install -r requirements.txt
python gui.py
```

CLI mode:

```powershell
python media_rescue.py "C:\MediaRescue\Originals" "C:\MediaRescue\Clean"
```

Output structure:

```text
Clean/
  Photos/      # Rebuilt JPEG/PNG files
  Videos/      # Re-encoded MP4 files
  report.csv   # Spreadsheet-readable per-file report
  report.html  # Self-contained human-readable report
```

## Build a Windows application

Install PyInstaller separately:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onedir --windowed --clean --noconfirm --name MediaRescue --collect-all PIL --collect-all pillow_heif --add-binary "bin\ffmpeg.exe;bin" --add-binary "bin\ffprobe.exe;bin" gui.py
```

Then test `dist\MediaRescue\MediaRescue.exe` on a clean Windows machine. Distribute the **entire** `dist\MediaRescue` folder as a ZIP. Verify FFmpeg distribution licenses and notices before releasing a bundled build.

## Automated tests

```powershell
python -m unittest discover -s tests -v
```

Existing tests should be rerun after each update. Tests and successful conversion do not prove resistance to unknown malicious media.

## Limitations and privacy

- Some malformed, animated, unsupported or oversized media will be rejected or skipped.
- Metadata (including location and original camera details), quality, and orientation may change.
- Video validation reads container metadata; it is not a malware scan.
- Rebuilding does not guarantee safe media or prove a device is free of spyware.
- MediaRescue processes media locally, and reports are saved locally. Optional Defender scanning invokes the Windows security service.

For vulnerability disclosures, see [SECURITY.md](SECURITY.md). The application's source license is described in [LICENSE](LICENSE); included third-party binaries retain their own licenses.
