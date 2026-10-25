"""Optional Windows Defender scan. No scanning occurs unless explicitly requested.

Uses MpCmdRun's -DisableRemediation, so MediaRescue does not change
Defender quarantine/remediation state. A nonzero exit code fails closed.
"""
from pathlib import Path
import os
import subprocess
import sys
import time


class DefenderScanError(RuntimeError):
    pass


class DefenderScanCancelled(DefenderScanError):
    pass


def find_defender():
    if sys.platform != 'win32':
        raise DefenderScanError('Microsoft Defender integration requires Windows.')
    program_data = Path(os.environ.get('ProgramData', r'C:\ProgramData'))
    platform = program_data / 'Microsoft' / 'Windows Defender' / 'Platform'
    if platform.is_dir():
        versions = sorted((p for p in platform.iterdir() if p.is_dir()), reverse=True)
        for version in versions:
            binary = version / 'MpCmdRun.exe'
            if binary.is_file():
                return binary
    program_files = Path(os.environ.get('ProgramFiles', r'C:\Program Files'))
    fallback = program_files / 'Windows Defender' / 'MpCmdRun.exe'
    if fallback.is_file():
        return fallback
    raise DefenderScanError('Microsoft Defender command-line scanner not found.')


def scan_folder(folder, cancel_event=None, log=None):
    """Return only on reported success; nonzero/cancel/error raises exception.

    NOTE: A successful scan is not a Pegasus-free certification.
    """
    path = Path(folder).resolve()
    if not path.is_dir():
        raise DefenderScanError('The scan folder does not exist.')
    if cancel_event is not None and cancel_event.is_set():
        raise DefenderScanCancelled('Cancelled before Defender scan.')
    exe = find_defender()
    command = [str(exe), '-Scan', '-ScanType', '3', '-File', str(path),
               '-DisableRemediation']
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    # No shell, no command injection from user-selected folder names.
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                errors='replace', stdin=subprocess.DEVNULL,
                                creationflags=flags)
    except OSError as exc:
        raise DefenderScanError(f'Cannot start Defender: {exc}') from exc
    try:
        # communicate(timeout) avoids blocking on a full stdout pipe.
        deadline = time.monotonic() + 3600
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise DefenderScanCancelled('Defender scan cancelled by user.')
            try:
                output, _ = proc.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() > deadline:
                    raise DefenderScanError('Defender scan exceeded the one-hour limit.')
        if proc.returncode != 0:
            excerpt = (output or '').strip()[-1200:]
            raise DefenderScanError(
                f'Defender returned code {proc.returncode}. A detection, scan error, '
                f'or action-required state may have occurred. Review Windows Security. '
                f'{excerpt}'
            )
        if log:
            log('Defender scan completed without reporting a detection. '
                'This does not guarantee the files are safe.')
        return True
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
