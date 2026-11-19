"""Fork identity + upstream-unlink contract (kanban t_683db6ae).

Owner request: the plugin's user-visible identity is "Usage Quota II' Turbo"
and EVERY update/link path targets the owner's own fork
HaydenCupcake/hermes-quota-widget — never rarf/hermes-quota-plugin.

The internal id `quota` is deliberately unchanged (directory names, the
`hermes quota` CLI verb, the /quota route, ctx.storage keys, plugin.yaml
name/provides_commands, the /api/plugins/quota backend namespace): the
rename is display-only plus catalog identity.

Legal attribution (LICENSE, plugin.yaml author) and historical docs
citations are allowlisted below; they are not update paths. Machine-local
install metadata (.hermes-catalog.json, version.json, caches) is not
shipped code and is verified separately at install time.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "Usage Quota II' Turbo"
UPSTREAM = "rarf/hermes-quota-plugin"
FORK = "HaydenCupcake/hermes-quota-widget"
FORK_URL = f"https://github.com/{FORK}"
FORK_API = f"https://api.github.com/repos/{FORK}/commits/master"

# Attribution + historical citations only — never update guidance.
ALLOWLIST = {"LICENSE", "plugin.yaml", "docs/contributors.md", "docs/security.md"}
# This guard must name the forbidden string to forbid it.
SELF = "tests/test_upstream_unlink.py"
# Machine-local install/runtime metadata, not shipped code (never committed).
MACHINE_LOCAL = {".hermes-catalog.json", "version.json", "quota_cache.json",
                 "quota_cache.json.tmp", ".widget-fixture.json"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "images"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pyc"}


def repo_text_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in MACHINE_LOCAL or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        yield rel.as_posix(), path


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class UpstreamUnlinkTests(unittest.TestCase):
    def test_allowlist_files_exist(self):
        for rel in sorted(ALLOWLIST):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_no_upstream_path_in_shipped_code(self):
        offenders = []
        for rel, path in repo_text_files():
            if rel in ALLOWLIST or rel == SELF:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if UPSTREAM in text:
                offenders.append(rel)
        self.assertEqual(offenders, [], f"upstream repo path survives in: {offenders}")

    def test_update_paths_explicitly_clean(self):
        for rel in ("desktop/plugin.js", "install.sh", "uninstall.sh",
                    "scripts/scan_plugin.py", "scripts/render-banner.sh",
                    "docs/installation.md", "README.md"):
            self.assertNotIn(UPSTREAM, read(rel), rel)

    def test_widget_self_check_targets_fork_only(self):
        src = read("desktop/plugin.js")
        m = re.search(r'REPO_API_LATEST\s*=\s*"([^"]+)"', src)
        self.assertIsNotNone(m, "REPO_API_LATEST constant missing")
        self.assertEqual(m.group(1), FORK_API)
        externals = re.findall(r'host\.openExternal\?\.\("([^"]+)"\)', src)
        self.assertEqual(externals, [FORK_URL],
                         "the update banner must open the fork, and nothing else")

    def test_scan_source_label_is_fork(self):
        self.assertIn(f'source="{FORK}/community"', read("scripts/scan_plugin.py"))

    def test_install_instructions_clone_fork(self):
        for rel in ("README.md", "docs/installation.md"):
            self.assertIn(f"git clone {FORK_URL}.git", read(rel), rel)
        self.assertIn("cd hermes-quota-widget", read("docs/installation.md"))

    def test_install_sh_keeps_local_head_stamp(self):
        text = read("install.sh")
        self.assertIn("rev-parse HEAD", text)
        self.assertIn("installed_sha", text)
        self.assertIn("version.json", text)


class DisplayNameTests(unittest.TestCase):
    def setUp(self):
        self.src = read("desktop/plugin.js")

    def test_default_export_name(self):
        self.assertIn(f'name: "{NAME}"', self.src)

    def test_pane_and_settings_titles(self):
        self.assertIn(f'paneTitle: "{NAME}"', self.src)
        self.assertIn(f'settingsTitle: "{NAME} · Settings"', self.src)

    def test_sidebar_nav_label_and_docked_pane_title(self):
        self.assertIn(f'label: "{NAME}"', self.src)
        self.assertIn(f'title: "{NAME}"', self.src)

    def test_statusbar_chip_text_and_aria_label(self):
        self.assertIn(f'children: "{NAME}"', self.src)
        self.assertIn(f'"aria-label": "{NAME} · Open {NAME} pane"', self.src)

    def test_tooltip_headers_and_lines(self):
        for needle in (f"{NAME} overview", f"Open the {NAME} pane →",
                       f"{NAME} · lowest", f"{NAME} breakdown:",
                       f"Click to open {NAME} pane", f"{NAME} settings",
                       f"{NAME} backend unavailable", f"Show {NAME} in sidebar",
                       f"Adds a {NAME} row", f"Back to {NAME}"):
            self.assertIn(needle, self.src)

    def test_old_display_wording_absent_from_widget(self):
        for needle in ('"Quota Widget"', 'paneTitle: "Quota"',
                       'settingsTitle: "Quota', '"Quota overview"',
                       'Open Quota pane', 'Open the Quota pane',
                       'Quota · lowest', 'Quota breakdown',
                       'Click to open Quota pane', 'settingsTip: "Quota settings"',
                       'Quota backend unavailable', 'Show Quota in sidebar',
                       'Adds a Quota row', 'label: "Quota"', 'title: "quota"',
                       'children: "Quota"', 'Back to quota'):
            self.assertNotIn(needle, self.src)

    def test_readme_title_intro_and_alts(self):
        readme = read("README.md")
        self.assertTrue(readme.startswith(f"# {NAME}\n"), "README title")
        self.assertIn(f"**{NAME}** shows provider quotas", readme)
        self.assertIn(f"![{NAME} in Hermes Desktop]", readme)
        self.assertIn(f"![{NAME} docked pane]", readme)
        self.assertNotIn("Hermes Quota", readme)

    def test_docs_headings_and_pane_references(self):
        self.assertIn(f"### {NAME} pane", read("docs/usage.md"))
        self.assertIn(f"in the {NAME} pane.", read("docs/troubleshooting.md"))

    def test_installer_messages_use_new_name(self):
        install = read("install.sh")
        uninstall = read("uninstall.sh")
        self.assertIn(f"{NAME} plugin installed", install)
        self.assertIn(f"{NAME} installation failed", install)
        self.assertIn(f"{NAME} plugin removed", uninstall)
        self.assertIn(f"{NAME} uninstall failed", uninstall)

    def test_banner_script_name_and_repo(self):
        text = read("scripts/render-banner.sh")
        self.assertIn(NAME, text)
        self.assertIn(f"github.com/{FORK}", text)
        self.assertNotIn("Hermes Quota", text)


class InternalIdStabilityTests(unittest.TestCase):
    """The rename is display-only: internal ids/routes/storage must not churn."""

    def test_widget_internal_id_routes_and_storage(self):
        src = read("desktop/plugin.js")
        self.assertIn('const ID = "quota"', src)
        self.assertIn('path: "/quota"', src)
        self.assertIn('window.location.hash === "#/quota"', src)
        self.assertIn('const QUOTA_QUERY_KEY = ["quota", "widget"]', src)
        self.assertIn('const SNAPSHOT_KEY = "lastPayload"', src)
        self.assertIn('const RESET_FORMAT_KEY = "resetFormat"', src)
        self.assertIn('const DISABLED_PROVIDERS_KEY = "disabledProviders"', src)
        self.assertIn('const SHOW_STATUSBAR_KEY = "showStatusBar"', src)
        self.assertIn('const SHOW_DOCKED_PANE_KEY = "showDockedPane"', src)
        self.assertIn('const SHOW_SIDEBAR_NAV_KEY = "showSidebarNav"', src)
        self.assertIn('const STATUSBAR_MODE_KEY = "statusbarMode"', src)
        self.assertIn('const PANE_DETAIL_KEY = "paneDetail"', src)
        self.assertIn('const REFRESH_INTERVAL_KEY = "refreshInterval"', src)

    def test_manifest_id_command_and_no_update_url(self):
        text = read("plugin.yaml")
        self.assertIn("name: quota", text)
        self.assertIn("- quota", text)
        self.assertNotIn("update_url", text)


if __name__ == "__main__":
    unittest.main()
