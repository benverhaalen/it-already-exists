"""Compiler-context publication refuses corrupt and unsafe reviewed inputs."""
import hashlib
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

source = Path(__file__).resolve().parents[1]/'skills/reference-driven-development/runtimes/android/prepare.py'
spec = importlib.util.spec_from_file_location('android_prepare', source)
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)


class AndroidContextTests(unittest.TestCase):
    def test_altered_dependencies_cannot_create_context(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root/'tools.zip'; archive.write_bytes(b'changed')
            platform = root/'android.jar'; platform.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'reviewed'):
                prepare.prepare(archive, platform, root/'context')
            self.assertFalse((root/'context').exists())

    def test_unsafe_archive_does_not_publish_partial_context(self):
        for unsafe in ('android-15/../../escape', '/absolute', 'android-15/link'):
            with self.subTest(unsafe=unsafe), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); archive = root/'tools.zip'; platform = root/'android.jar'
                platform.write_bytes(b'compiler stub')
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr('android-15/ordinary', b'first valid entry')
                    info = zipfile.ZipInfo(unsafe)
                    if unsafe.endswith('/link'):
                        info.create_system = 3; info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    z.writestr(info, b'withheld path')
                with patch.object(prepare, 'BUILD_TOOLS_SHA256', hashlib.sha256(archive.read_bytes()).hexdigest()), \
                     patch.object(prepare, 'PLATFORM_SHA256', hashlib.sha256(platform.read_bytes()).hexdigest()):
                    with self.assertRaisesRegex(ValueError, 'unsafe'):
                        prepare.prepare(archive, platform, root/'context')
                self.assertFalse((root/'context').exists())
                self.assertFalse((root/'escape').exists())


if __name__ == '__main__':
    unittest.main()
