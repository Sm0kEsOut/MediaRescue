"""Local, human-readable HTML reports; no external resources or uploads."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path


def write_html_report(path, results, *, total, cancelled):
    """Write a self-contained HTML report from [source, status, details] rows."""
    path = Path(path)
    counts = Counter(row[1] for row in results)
    pending = max(0, total - len(results))
    rows = []
    for source, status, details in results:
        if status == 'REBUILT':
            css = 'good'
        elif status == 'REJECTED':
            css = 'bad'
        else:
            css = 'muted'
        rows.append('<tr><td>{}</td><td class="{}">{}</td><td>{}</td></tr>'.format(
            escape(str(source)), css, escape(str(status)), escape(str(details))))
    report_status = 'Cancelled' if cancelled else 'Processing finished'
    markup = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediaRescue — Reconstruction Report</title>
<style>body{font-family:system-ui,'Segoe UI',sans-serif;margin:2rem auto;max-width:1050px;padding:0 1rem;color:#18202d;background:#f8fafc}h1{margin-bottom:.25rem}p{line-height:1.5}.note{background:#fff5db;border-left:4px solid #9c6900;padding:1rem}.metrics{display:flex;gap:.75rem;flex-wrap:wrap;margin:1.5rem 0}.metric{background:white;padding:1rem 1.25rem;border:1px solid #ddd;border-radius:10px;min-width:110px}.metric b{font-size:1.5rem;display:block}table{border-collapse:collapse;background:white;width:100%;table-layout:fixed}th,td{text-align:left;padding:.7rem;vertical-align:top;border-bottom:1px solid #ddd;overflow-wrap:anywhere}th{background:#e9eef5}.good{color:#166534;font-weight:600}.bad{color:#a31515;font-weight:600}.muted{color:#596579}small{color:#506076}</style></head><body>
<h1>MediaRescue Report</h1><p>''' + escape(report_status) + ''' · Generated ''' + escape(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')) + '''</p>
<div class="note"><strong>Important:</strong> REBUILT means converted, <strong>not malware-free</strong>. MediaRescue does not detect Pegasus or certify files as safe. This report records reconstruction only; it is not evidence of a completed Microsoft Defender scan. Check Defender's log and Windows Security separately.</div>
<div class="metrics"><div class="metric"><b>''' + str(total) + '''</b>Found</div><div class="metric"><b>''' + str(counts['REBUILT']) + '''</b>Rebuilt</div><div class="metric"><b>''' + str(counts['REJECTED']) + '''</b>Rejected</div><div class="metric"><b>''' + str(counts['SKIPPED']) + '''</b>Skipped</div><div class="metric"><b>''' + str(pending) + '''</b>Unprocessed</div></div>
<h2>Files</h2><table><thead><tr><th style="width:35%">Original file</th><th style="width:13%">Result</th><th>Details / output</th></tr></thead><tbody>''' + ('\n'.join(rows) if rows else '<tr><td colspan="3">No files processed</td></tr>') + '''</tbody></table>
<p><small>Local report. No external scripts, fonts, or network resources. Paths and filenames can contain sensitive information; do not publicly share this report.</small></p></body></html>'''
    temporary = path.with_suffix('.html.tmp')
    temporary.write_text(markup, encoding='utf-8')
    temporary.replace(path)
    return str(path)
