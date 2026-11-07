"""Check computed tooltip colors in Chromium in Hermes glass mode."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from widget_harness import render, nodes

CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser")

@unittest.skipUnless(CHROMIUM, "Chromium unavailable")
class TooltipBackgroundTests(unittest.TestCase):
    def test_glass_light_and_dark_background_and_arrow(self):
        tree = render(component="status", data={"age_s": 0, "providers": {"nous": {"windows": []}}})
        styles = next(n for n in nodes(tree) if n.get("type") == "Tip")["props"]["style"]
        for color in ("rgb(246, 246, 246)", "rgb(32, 32, 32)"):
            with self.subTest(color=color), tempfile.TemporaryDirectory() as tmp:
                markup = f'''<!doctype html><div id="popup"><div id="arrow"></div></div><pre id="result"></pre><script>
                const root = document.documentElement.style;
                root.setProperty("--ui-editor-surface-background", "transparent");
                root.setProperty("--ui-bg-elevated", {json.dumps(color)});
                const popup = document.getElementById("popup");
                const styles = {json.dumps(styles)};
                for (const [k,v] of Object.entries(styles)) {{ if (k.startsWith("--")) popup.style.setProperty(k,v); else popup.style[k]=v; }}
                const arrow = document.getElementById("arrow"); arrow.style.background = "var(--foreground)";
                document.getElementById("result").textContent = JSON.stringify([getComputedStyle(popup).backgroundColor, getComputedStyle(arrow).backgroundColor]);
                </script>'''
                page = Path(tmp) / "test.html"
                page.write_text(markup)
                result = subprocess.run([CHROMIUM, "--headless", "--no-sandbox", "--disable-gpu", "--dump-dom", page.as_uri()], text=True, capture_output=True, timeout=30, check=True)
                match = re.search(r'<pre id="result">(.*?)</pre>', result.stdout)
                self.assertIsNotNone(match)
                self.assertEqual(json.loads(match.group(1)), [color, color])
