"""A failed refresh must not hide a valid quota snapshot.

Nov-7 leftover probe, dispositioned by t_022cc145. The keep-values-with-
warning contract lives in the statusbar hover dashboard (QuotaMiniTip),
whose vocabulary this probe quotes ("Refresh failed · retrying", the
"(cached)" stale marking). The original render() call defaulted to
QuotaPane, whose isError body fails closed to "backend unavailable" by
design, and text() sees neither Tip labels nor aria/title props -- so the
probe could never observe the contract it asserted, on the fork or on
upstream 3.0.0. Retargeted to the status surface with tooltip_text() plus
structural stale assertions; the no-snapshot pane test is unchanged. The
pane's fail-closed body is a separate product finding (documented in the
triage report), deliberately not pinned here.
"""
import unittest
from widget_harness import render, nodes, text, tooltip_text

SNAPSHOT = {
    "fetched_at": "2026-10-20T16:44:19Z", "age_s": 50,
    "providers": {"opencode-go": {
        "label": "opencode-go",
        "windows": [{"label": "Weekly", "used_percent": 25}],
        "details": [], "unavailable_reason": None}},
}


class CachedRefreshErrorTests(unittest.TestCase):
    def test_failed_refresh_keeps_saved_values_with_warning(self):
        tree = render(component="status", data=SNAPSHOT, isError=True)
        tip = tooltip_text(tree)
        # The saved window survives the failed refresh, with its value.
        self.assertIn("75% left", tip)
        # ...and the failure is announced, not hidden.
        self.assertIn("Refresh failed", tip)
        # The cached marking is structural (aria-label/title), not body
        # text: stale bars carry "(cached)" and keep the saved value.
        label = next(n["props"]["label"] for n in nodes(tree)
                     if n.get("type") == "Tip")
        bars = [n for n in nodes(label)
                if n.get("props", {}).get("role") == "progressbar"]
        self.assertTrue(bars, "the saved window must still render a bar")
        self.assertTrue(
            any("(cached)" in (b["props"].get("aria-label") or "")
                for b in bars),
            "a stale snapshot must carry the cached marking")
        self.assertTrue(any(b["props"].get("aria-valuenow") == 75
                            for b in bars))
        self.assertNotIn("Usage Quota II' Turbo backend unavailable",
                         text(tree) + tip)

    def test_failure_without_snapshot_reports_unavailable(self):
        rendered = text(render(isError=True))
        self.assertIn("Usage Quota II' Turbo backend unavailable", rendered)
        self.assertNotIn("% left", rendered)


if __name__ == "__main__":
    unittest.main()
