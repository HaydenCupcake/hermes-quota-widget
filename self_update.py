"""Safely fast-forward an installed quota checkout and publish its desktop half."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FORK_ORIGIN = "https://github.com/HaydenCupcake/hermes-quota-widget"


def _write_json(path: Path, data: dict) -> None:
    # Replace the directory entry rather than writing through a possible link.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.quota-update-', delete=False) as out:
            temporary = Path(out.name)
            json.dump(data, out, indent=2)
            out.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _git(root: Path, *args: str) -> str:
    # A public fetch must not invoke credential helpers, prompts or checkout hooks.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull, "HOME": str(root / '.quota-no-home')})
    cmd = ['git', '-c', 'credential.helper=', '-c', f'core.hooksPath={os.devnull}',
           '-c', 'fetch.recurseSubmodules=false', '-C', str(root), *args]
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=75, env=env)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Git command failed').strip())
    return result.stdout.strip()


def self_update(root: Path, app_root: Path) -> dict:
    root = Path(root).resolve()
    try:
        top = Path(_git(root, 'rev-parse', '--show-toplevel')).resolve()
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        raise RuntimeError('Installation is not a Git checkout; reinstall from the fork to enable updates.') from exc
    if top != root:
        raise RuntimeError('Installation is not its own Git checkout; reinstall from the fork to enable updates.')
    if _git(root, 'remote', 'get-url', '--all', 'origin') != FORK_ORIGIN:
        raise RuntimeError('Update refused: origin is not the expected fork.')
    if _git(root, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Update refused: tracked files are dirty.')
    sidecar = root / '.hermes-catalog.json'
    metadata = None
    if sidecar.is_symlink():
        raise RuntimeError('Update refused: linked install metadata.')
    if sidecar.exists():
        try:
            metadata = json.loads(sidecar.read_text(encoding='utf-8-sig'))
            if not isinstance(metadata, dict) or metadata.get('repo') != FORK_ORIGIN:
                raise ValueError('unexpected origin')
        except (OSError, ValueError) as exc:
            raise RuntimeError('Update refused: invalid install metadata.') from exc
    from hermes_cli import desktop_plugin_halves as halves
    target = Path(app_root) / 'quota'
    source = root / 'desktop' / 'plugin.js'
    if not source.is_file():
        raise RuntimeError('Update refused: desktop source is missing.')
    # Adopt a byte-identical legacy installation before changing its source.
    # Never claim or replace an unrelated desktop plugin.
    with halves.ROOT_WRITER:
        marker = halves.read_package_marker(target)
        if target.exists():
            entry = target / 'plugin.js'
            if (not entry.is_file() or entry.read_bytes() != source.read_bytes() or
                    (marker and marker.get('source') != str(source.parent))):
                raise RuntimeError('Update refused: desktop plugin differs from this checkout.')
            if not marker:
                halves.materialize_desktop_half(root, Path(app_root), 'quota')
                if not halves.read_package_marker(target):
                    raise RuntimeError('Update refused: desktop plugin cannot be safely adopted.')
    before = _git(root, 'rev-parse', 'HEAD')
    _git(root, 'update-ref', 'refs/heads/backup/pre-self-update-' + before, before)
    _git(root, 'fetch', '--no-tags', 'origin', 'master')
    _git(root, 'merge', '--ff-only', 'FETCH_HEAD')
    after = _git(root, 'rev-parse', 'HEAD')
    changed = _git(root, 'diff', '--name-only', before, after).splitlines()
    stamp = {'installed_sha': after, 'installed_commit_date': _git(root, 'show', '-s', '--format=%cI', 'HEAD'),
             'installed_at': datetime.now(timezone.utc).isoformat()}
    _write_json(root / 'version.json', stamp)
    if metadata is not None:
        metadata['sha'] = after
        _write_json(sidecar, metadata)
    with halves.ROOT_WRITER:
        halves.materialize_desktop_half(root, Path(app_root), 'quota')
        marker = halves.read_package_marker(target)
        if marker and marker.get('source') == str(source.parent) and metadata is not None:
            marker['sha'] = after
            halves._write_marker(target, marker)
    marker = halves.read_package_marker(target)
    synced = bool(marker and marker.get('source') == str(root / 'desktop') and
                  (target / 'plugin.js').read_bytes() == (root / 'desktop' / 'plugin.js').read_bytes())
    if not synced:
        raise RuntimeError('Git update completed, but the desktop widget could not be synchronized; check the installed desktop plugin.')
    return {'updated': before != after, 'from_sha': before, 'to_sha': after,
            'changed_files': changed,
            'backend_changed': any(p.endswith('.py') and not p.startswith('tests/') for p in changed),
            'widget_synced': synced, 'stamp': stamp}
