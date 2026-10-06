import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class EntrypointTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'prisma', *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    def test_module_help(self):
        result = self.run_cli('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('panel', result.stdout)
    def test_module_generate_and_check(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_cli('generate', '--out', folder, '--customers', '24', '--seed', '42')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(folder) / 'prisma_demo.sqlite').is_file())
            result = self.run_cli('check', '--data', folder)
            self.assertEqual(result.returncode, 0, result.stderr)
