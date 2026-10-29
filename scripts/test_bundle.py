from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

import bundle


class BundleTest(unittest.TestCase):
    def test_host_aliases(self):
        for system, arch, expected in [
            ('Linux', 'x86_64', 'linux-x86_64'), ('Linux', 'aarch64', 'linux-aarch64'),
            ('Darwin', 'arm64', 'macos-aarch64'), ('Darwin', 'x86_64', 'macos-x86_64'),
            ('Windows', 'AMD64', 'windows-x86_64')]:
            with self.subTest(system=system, arch=arch):
                self.assertEqual(bundle.host_platform(system, arch), expected)
        with self.assertRaises(ValueError):
            bundle.host_platform('Windows', 'ARM64')

    def test_mat_layouts(self):
        for layout in ('mat', 'mat.app/Contents/Eclipse', 'MemoryAnalyzer.app/Contents/Eclipse'):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                runtime = root / layout
                (runtime / 'plugins').mkdir(parents=True)
                (runtime / 'plugins/org.eclipse.equinox.launcher_1.jar').touch()
                config = runtime / 'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
                config.parent.mkdir(parents=True)
                config.touch()
                self.assertEqual(bundle.locate_mat(root), runtime)

    def test_jre_layouts(self):
        for target, layout, binary in [
            ('linux-aarch64', 'jdk-jre', 'java'),
            ('macos-aarch64', 'jdk-jre/Contents/Home', 'java'),
            ('windows-x86_64', 'jdk-jre', 'java.exe')]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                runtime = root / layout
                (runtime / 'bin').mkdir(parents=True)
                (runtime / 'bin' / binary).touch()
                self.assertEqual(bundle.locate_jre(root, target), runtime)

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr('../escape', 'no')
            with self.assertRaises(ValueError):
                bundle.extract_zip(archive, root / 'output')
            self.assertFalse((root / 'escape').exists())

    def test_zip_unsafe_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'bad.zip'
            info = zipfile.ZipInfo('link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr(info, '../../escape')
            with self.assertRaises(ValueError):
                bundle.extract_zip(archive, root / 'output')

    @unittest.skipIf(__import__('os').name == 'nt', 'Unix execute bits')
    def test_zip_execute_bits_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'runtime.zip'
            info = zipfile.ZipInfo('bin/java')
            info.external_attr = (stat.S_IFREG | 0o755) << 16
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr(info, 'fixture')
            bundle.extract_zip(archive, root / 'output')
            self.assertEqual((root / 'output/bin/java').stat().st_mode & 0o777, 0o755)

    def test_plugin_registration_preserves_existing_bundles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / 'mat'
            (runtime / 'plugins').mkdir(parents=True)
            config = runtime / 'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
            config.parent.mkdir(parents=True)
            config.write_text('#version=1\nother,1,plugins/other.jar,4,false\nCliMatPlugin,old,old.jar,4,false\n')
            plugin = root / 'plugin.jar'
            with zipfile.ZipFile(plugin, 'w') as stream:
                stream.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\nBundle-Version: 2.1.0\n')
            bundle.install_plugin(runtime, plugin)
            bundle.install_plugin(runtime, plugin)
            lines = config.read_text().splitlines()
            self.assertIn('other,1,plugins/other.jar,4,false', lines)
            self.assertEqual(len([line for line in lines if line.startswith('CliMatPlugin,')]), 1)
            self.assertEqual((runtime / 'plugins/CliMatPlugin_2.1.0.jar').read_bytes(), plugin.read_bytes())

    def test_all_targets_pin_official_downloads(self):
        self.assertEqual(len(bundle.LOCK['platforms']), 5)
        for spec in bundle.LOCK['platforms'].values():
            self.assertTrue(spec['mat']['url'].startswith('https://download.eclipse.org/mat/1.17.0/'))
            self.assertEqual(len(spec['mat']['sha512']), 128)
            self.assertTrue(spec['jre']['url'].startswith('https://github.com/adoptium/temurin21-binaries/'))
            self.assertEqual(len(spec['jre']['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
