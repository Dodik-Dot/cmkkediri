from pathlib import Path
import re
import subprocess
import tempfile
import unittest

INSTALLER = Path(__file__).parents[1] / 'linux/install.sh'

class InstallerTests(unittest.TestCase):
    def test_help_and_invalid_arguments_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            check = root / 'local' / 'other-team.sh'
            check.parent.mkdir()
            check.write_text('keep me')
            cache = root / 'cache' / 'other-cache'
            cache.parent.mkdir()
            cache.write_text('cached data')
            # All paths redirected; no root/system installation is performed.
            source = INSTALLER.read_text()
            source = source.replace('if [ "$EUID" -ne 0 ]; then', 'if false; then')
            source = source.replace('/usr/lib/check_mk_agent/local', str(check.parent))
            source = source.replace('/var/lib/check_mk_agent/cache', str(cache.parent))
            script = root / 'install.sh'
            script.write_text(source)
            for args, expected in [(['--help'], 0), (['--invalid'], 1), (['--server'], 1)]:
                result = subprocess.run(['bash', str(script)] + args, capture_output=True, timeout=3)
                self.assertEqual(result.returncode, expected)
                self.assertEqual(check.read_text(), 'keep me')
                self.assertEqual(cache.read_text(), 'cached data')

    def test_atomic_download_preserves_old_file_on_failure(self):
        source = INSTALLER.read_text()
        function = re.search(r'download_atomic\(\) \{\n.*?\n\}', source, re.S).group()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'check.sh'
            target.write_text('old')
            failed_curl = 'curl() { printf partial > "${@: -1}"; return 22; }\n'
            command = function + '\n' + failed_curl + 'download_atomic https://example.invalid "$1"'
            result = subprocess.run(['bash', '-c', command, 'test', str(target)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), 'old')
            self.assertEqual(list(target.parent.iterdir()), [target])
            good_curl = 'curl() { printf new > "${@: -1}"; }\n'
            command = function + '\n' + good_curl + 'download_atomic https://example.invalid "$1"'
            result = subprocess.run(['bash', '-c', command, 'test', str(target)], capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), 'new')
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)

if __name__ == '__main__':
    unittest.main()
