# Human-readable report update

This update is based on the previous Defender integration and includes updated `gui.py`, `media_rescue.py`, `defender_scan.py`, plus a new `reporting.py` and `README.md`.

1. Back up your project's current Python files and README.
2. Copy the files from this package into the repository root.
3. Keep existing `bin/`, `tests/`, `requirements.txt`, `.gitignore`, `SECURITY.md`, and `LICENSE`.
4. Run `python gui.py` and test with ordinary sample media.
5. Confirm `report.html` and `report.csv` appear in the output folder and the GUI's **Open HTML Report** button works.
6. Run your automated tests and rebuild your exe as described in README.

Reports are generated from the same records. Defender status is intentionally not misrepresented as proof of cleanliness. A cancellation during the initial Defender scan may not generate a reconstruction report, because reconstruction never started.

**Note:** `report.html` includes original file paths. Don't publish reports containing personal information.
