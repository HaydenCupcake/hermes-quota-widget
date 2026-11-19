"""Offline real-Git self-update contract tests. No network or live installation."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import sys
import argparse
import contextlib
import io
import importlib
import threading
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('quota_self_update', ROOT / 'self_update.py')
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)
FORK = 'https://github.com/HaydenCupcake/hermes-quota-widget'
package = types.ModuleType('quota_selfupdate_test')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
try:
    import hermes_constants  # noqa: F401
except ImportError:
    constants = types.ModuleType('hermes_constants')
    constants.get_hermes_home = lambda: Path(tempfile.gettempdir())
    sys.modules['hermes_constants'] = constants
commands = importlib.import_module('quota_selfupdate_test.commands')


def fallback_halves():
    """Offline stand-in when the Hermes core is absent, as in plugin CI.

    On a Hermes host these same fixtures exercise the real core writer instead.
    """
    halves = types.ModuleType('hermes_cli.desktop_plugin_halves')
    halves.ROOT_WRITER = threading.Lock()
    def read_marker(target):
        try:
            return json.loads((target / '.hermes-package.json').read_text())
        except (OSError, ValueError):
            return None
    def write_marker(target, marker):
        (target / '.hermes-package.json').write_text(json.dumps(marker))
    def materialize(root, app, name):
        source, target = root / 'desktop', app / name
        existing = read_marker(target)
        if target.exists() and not existing and (target / 'plugin.js').read_bytes() != (source / 'plugin.js').read_bytes():
            return None
        target.mkdir(parents=True, exist_ok=True)
        (target / 'plugin.js').write_bytes((source / 'plugin.js').read_bytes())
        marker = {'package': name, 'source': str(source), 'sourceMtimeMs': (source / 'plugin.js').stat().st_mtime * 1000}
        sidecar = root / '.hermes-catalog.json'
        if sidecar.exists():
            marker.update(json.loads(sidecar.read_text()))
        write_marker(target, marker)
        return target
    halves.read_package_marker = read_marker
    halves._write_marker = write_marker
    halves.materialize_desktop_half = materialize
    return halves


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class SelfUpdateTests(unittest.TestCase):
    def setUp(self):
        try:
            import hermes_cli.desktop_plugin_halves  # noqa: F401
        except ImportError:
            pkg = types.ModuleType('hermes_cli')
            pkg.__path__ = []
            pkg.desktop_plugin_halves = fallback_halves()
            core = patch.dict(sys.modules, {'hermes_cli': pkg, 'hermes_cli.desktop_plugin_halves': pkg.desktop_plugin_halves})
            core.start()
            self.addCleanup(core.stop)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.remote = self.base / 'remote'
        self.clone = self.base / 'quota'
        self.app = self.base / 'desktop-plugins'
        self.remote.mkdir()
        git(self.remote, 'init', '-b', 'master')
        git(self.remote, 'config', 'user.name', 'Test')
        git(self.remote, 'config', 'user.email', 'test@example.invalid')
        (self.remote / 'desktop').mkdir()
        (self.remote / 'desktop/plugin.js').write_text('old', encoding='utf-8')
        (self.remote / 'commands.py').write_text('old', encoding='utf-8')
        git(self.remote, 'add', '.')
        git(self.remote, 'commit', '-m', 'old')
        subprocess.run(['git', 'clone', '--quiet', str(self.remote), str(self.clone)], check=True)
        git(self.clone, 'config', 'user.name', 'Test')
        git(self.clone, 'config', 'user.email', 'test@example.invalid')
        git(self.clone, 'remote', 'set-url', 'origin', FORK)
        self.old = git(self.clone, 'rev-parse', 'HEAD')
        self.fetch_calls = []
        original = update._git
        def fixture_git(root, *args):
            if args == ('fetch', '--no-tags', 'origin', 'master'):
                self.fetch_calls.append(args)
                return original(root, 'fetch', '--no-tags', str(self.remote), 'master')
            return original(root, *args)
        self.patcher = patch.object(update, '_git', side_effect=fixture_git)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def advance(self, path='commands.py'):
        target = self.remote / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('new', encoding='utf-8')
        git(self.remote, 'add', '.')
        git(self.remote, 'commit', '-m', 'new')
        return git(self.remote, 'rev-parse', 'HEAD')

    def run_update(self):
        return update.self_update(self.clone, self.app)

    def test_fast_forward_stamps_backup_and_syncs(self):
        new = self.advance()
        result = self.run_update()
        self.assertTrue(result['updated'])
        self.assertEqual((result['from_sha'], result['to_sha']), (self.old, new))
        self.assertEqual(result['changed_files'], ['commands.py'])
        self.assertTrue(result['backend_changed'])
        self.assertTrue(result['widget_synced'])
        self.assertEqual(git(self.clone, 'rev-parse', 'backup/pre-self-update-' + self.old), self.old)
        stamp = json.loads((self.clone / 'version.json').read_text(encoding='utf-8'))
        self.assertEqual(stamp['installed_sha'], new)
        self.assertEqual(stamp['installed_commit_date'], git(self.clone, 'show', '-s', '--format=%cI', 'HEAD'))
        self.assertIn('installed_at', stamp)
        self.assertEqual(result['stamp'], stamp)
        self.assertEqual((self.app / 'quota/plugin.js').read_text(), 'old')
        marker = json.loads((self.app / 'quota/.hermes-package.json').read_text())
        self.assertEqual(marker['source'], str(self.clone / 'desktop'))
        self.assertEqual(marker['package'], 'quota')

    def test_wrong_origin_refuses_without_fetch(self):
        git(self.clone, 'remote', 'set-url', 'origin', 'https://example.invalid/not-fork')
        with self.assertRaisesRegex(Exception, 'origin'):
            self.run_update()
        self.assertEqual(self.fetch_calls, [])
        self.assertEqual(git(self.clone, 'rev-parse', 'HEAD'), self.old)

    def test_dirty_tracked_refuses_without_fetch(self):
        (self.clone / 'commands.py').write_text('dirty')
        with self.assertRaisesRegex(Exception, 'dirty'):
            self.run_update()
        self.assertEqual(self.fetch_calls, [])
        self.assertEqual(git(self.clone, 'rev-parse', 'HEAD'), self.old)

    def test_divergence_refuses_without_forcing_local_commit(self):
        self.advance()
        (self.clone / 'local.txt').write_text('local')
        git(self.clone, 'add', 'local.txt')
        git(self.clone, 'commit', '-m', 'local')
        local = git(self.clone, 'rev-parse', 'HEAD')
        with self.assertRaises(Exception):
            self.run_update()
        self.assertEqual(git(self.clone, 'rev-parse', 'HEAD'), local)
        self.assertEqual(git(self.clone, 'rev-parse', 'backup/pre-self-update-' + local), local)

    def test_test_only_python_change_does_not_require_restart(self):
        self.advance('tests/check.py')
        result = self.run_update()
        self.assertEqual(result['changed_files'], ['tests/check.py'])
        self.assertFalse(result['backend_changed'])

    def test_unmarked_matching_widget_is_adopted_before_merge(self):
        widget = self.app / 'quota'
        widget.mkdir(parents=True)
        (widget / 'plugin.js').write_text('old')
        self.advance('desktop/plugin.js')
        result = self.run_update()
        self.assertTrue(result['widget_synced'])
        self.assertEqual((widget / 'plugin.js').read_text(), 'new')

    def test_unmarked_different_widget_refuses_before_fetch(self):
        widget = self.app / 'quota'
        widget.mkdir(parents=True)
        (widget / 'plugin.js').write_text('foreign')
        self.advance('desktop/plugin.js')
        with self.assertRaisesRegex(Exception, 'desktop'):
            self.run_update()
        self.assertEqual(self.fetch_calls, [])
        self.assertEqual(git(self.clone, 'rev-parse', 'HEAD'), self.old)
        self.assertEqual((widget / 'plugin.js').read_text(), 'foreign')

    def test_existing_origin_metadata_tracks_new_commit(self):
        sidecar = self.clone / '.hermes-catalog.json'
        sidecar.write_text(json.dumps({'repo': FORK, 'sha': self.old, 'catalog_name': 'quota'}))
        new = self.advance('desktop/plugin.js')
        self.run_update()
        marker = json.loads((self.app / 'quota/.hermes-package.json').read_text())
        self.assertEqual(json.loads(sidecar.read_text())['sha'], new)
        self.assertEqual(marker['sha'], new)

    def test_not_a_checkout_refuses(self):
        folder = self.base / 'copied-install'
        folder.mkdir()
        with self.assertRaisesRegex(Exception, 'Git checkout'):
            update.self_update(folder, self.app)


class CliContractTests(unittest.TestCase):
    def test_stamp_exposes_commit_date(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            root = Path(folder)
            (root / 'plugin.yaml').write_text('version: 2.11.0\n')
            (root / 'version.json').write_text(json.dumps({'installed_sha': 'abc', 'installed_commit_date': '2026-01-01T00:00:00Z'}))
            with patch.object(commands, '__file__', str(root / 'commands.py')):
                stamp = commands._plugin_stamp()
            self.assertEqual(stamp['installed_sha'], 'abc')
            self.assertEqual(stamp['installed_date'], '2026-01-01T00:00:00Z')

    def test_cli_dispatch_returns_structured_result(self):
        parser = argparse.ArgumentParser()
        commands.setup_argparse(parser)
        args = parser.parse_args(['self-update'])
        output = io.StringIO()
        desktop_install = types.ModuleType('hermes_cli.desktop_plugin_install')
        desktop_install.desktop_plugins_root = lambda: ROOT / 'unused-test-root'
        with patch.dict(sys.modules, {'hermes_cli.desktop_plugin_install': desktop_install}), patch('quota_selfupdate_test.self_update.self_update', return_value={'updated': True, 'backend_changed': False, 'widget_synced': True}), contextlib.redirect_stdout(output):
            commands._handle_cli(args)
        self.assertEqual(json.loads(output.getvalue())['updated'], True)


if __name__ == '__main__':
    unittest.main()
