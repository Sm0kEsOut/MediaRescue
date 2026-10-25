import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reporting import write_html_report

class ReportingTests(unittest.TestCase):
    def test_escapes_content_and_marks_cancelled(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / 'report.html'
            write_html_report(dest, [
                ('<script>alert(1)</script>.jpg', 'REJECTED', '<invalid>'),
                ('ok.jpg', 'REBUILT', 'ok-output.jpg'),
            ], total=5, cancelled=True)
            html = dest.read_text(encoding='utf-8')
            self.assertIn('Cancelled', html)
            self.assertIn('&lt;script&gt;', html)
            self.assertNotIn('<script>', html)
            self.assertIn('Unprocessed', html)
            self.assertIn('not malware-free', html)

    def test_empty_report(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / 'report.html'
            write_html_report(dest, [], total=0, cancelled=False)
            self.assertIn('No files processed', dest.read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
