"""Check computed Quota tooltip colors in Chromium with a glass editor."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from widget_harness import nodes, render

# An explicitly configured executable must fail loudly if it cannot be run.
CHROMIUM = os.environ.get("CHROMIUM") or shutil.which("chromium") or shutil.which("chromium-browser")


@unittest.skipUnless(CHROMIUM, "Chromium unavailable; set CHROMIUM to its executable")
class TooltipBackgroundTests(unittest.TestCase):
    def test_glass_light_and_dark_popup_and_arrow(self):
        data = {"age_s": 0, "providers": {"nous": {"windows": [{"label": "Weekly", "used_percent": 25}]}}}
        cases = {
            "status": {"component": "status", "data": data},
            "worst": {"component": "worst", "data": data},
            "provider": {"component": "chip", "id": "nous", "provider": data["providers"]["nous"]},
        }
        for callsite, options in cases.items():
            tips = [n for n in nodes(render(**options)) if n.get("type") == "Tip"]
            self.assertEqual(len(tips), 1, callsite)
            styles = tips[0]["props"]["style"]
            for theme, color in (("light", "rgb(246, 246, 246)"), ("dark", "rgb(32, 32, 32)")):
                with self.subTest(callsite=callsite, theme=theme), tempfile.TemporaryDirectory() as tmp:
                    # The SDK renders an SVG arrow and colors it with fill, not background.
                    markup = f'''<!doctype html><style>.tooltip-bubble [data-slot="tooltip-arrow"] {{ fill: var(--foreground); }}</style>
                    <div id="popup" class="tooltip-bubble"><svg data-slot="tooltip-arrow"><path d="M0 0h10L5 5Z"/></svg></div>
                    <pre id="result"></pre><script>
                    const root = document.documentElement.style;
                    root.setProperty("--ui-editor-surface-background", "transparent");
                    root.setProperty("--ui-bg-elevated", {json.dumps(color)});
                    const popup = document.getElementById("popup");
                    const styles = {json.dumps(styles)};
                    for (const [k,v] of Object.entries(styles)) {{ if (k.startsWith("--")) popup.style.setProperty(k,v); else popup.style[k]=v; }}
                    const arrow = popup.querySelector('[data-slot="tooltip-arrow"] path');
                    document.getElementById("result").textContent = JSON.stringify([getComputedStyle(popup).backgroundColor, getComputedStyle(arrow).fill]);
                    </script>'''
                    page = Path(tmp) / "test.html"
                    page.write_text(markup, encoding="utf-8")
                    result = subprocess.run([CHROMIUM, "--headless", "--no-sandbox", "--disable-gpu", f"--user-data-dir={Path(tmp) / 'profile'}", "--dump-dom", page.as_uri()], text=True, capture_output=True, timeout=30, check=True)
                    match = re.search(r'<pre id="result">(.*?)</pre>', result.stdout)
                    self.assertIsNotNone(match, result.stdout)
                    self.assertEqual(json.loads(match.group(1)), [color, color])


if __name__ == "__main__":
    unittest.main()
