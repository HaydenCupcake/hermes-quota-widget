"""Contract for the generic Quota chip and grouped SDK hover dashboard."""
import unittest
from widget_harness import render, nodes, text, tooltip_text


def windows(tree):
    return [n for n in nodes(tree) if n['props'].get('data-quota-mini-window')]


class WidgetTooltipTests(unittest.TestCase):
    def test_fractional_generic_window_never_claims_limit_reached(self):
        data = {'age_s': 0, 'providers': {'openai-codex': {'accounts': [
            {'windows': [{'label': 'Session', 'used_percent': 99.9},
                         {'label': 'Weekly', 'used_percent': 42}]}]}}}
        tree = render(component='status', data=data)
        tip = tooltip_text(tree)
        self.assertIn('Account 1', tip)
        session = next(n for n in windows(next(n['props']['label'] for n in nodes(tree) if n['type'] == 'Tip')) if n['props']['data-quota-mini-window'] == 'Session')
        self.assertIn('<1%', text(session))
        self.assertNotIn('limit reached', tip)
        progress = next(n for n in nodes(session) if n['props'].get('role') == 'progressbar')
        self.assertGreater(progress['props']['aria-valuenow'], 0)

    def test_compact_hover_preserves_all_categories_and_other_provider_info(self):
        data = {'age_s': 0, 'providers': {
            'openai-codex': {'accounts': [
                {'plan': 'pro', 'details': ['Banked resets: 2'], 'windows': [
                    {'label': 'Session', 'used_percent': 21},
                    {'label': 'Weekly', 'used_percent': 10},
                    {'label': '5.3 Codex Spark · Weekly', 'used_percent': 100}]}]},
            'anthropic': {'windows': [{'label': 'Weekly', 'used_percent': 60}]}}}
        for mode in ('all', 'worst'):
            tree = render(component='status', statusMode=mode, data=data)
            label = next(n['props']['label'] for n in nodes(tree) if n['type'] == 'Tip')
            categories = windows(label)
            self.assertEqual(len(categories), 4)
            for part in ('Session', '79%', '90%', '40%', '5.3 Codex Spark'):
                self.assertIn(part, tooltip_text(tree))
            for part in ('Banked resets', 'priority-eligible', 'inference routing'):
                self.assertNotIn(part, tooltip_text(tree))
        pane = text(render(data=data))
        for part in ('pro', 'Banked resets: 2', '5.3 Codex Spark'):
            self.assertIn(part, pane)

    def test_legacy_modes_both_use_one_generic_chip_with_all_accounts_in_sdk_tip(self):
        data = {'age_s': 0, 'providers': {'openai-codex': {'accounts': [
            {'windows': [{'label': 'Session', 'used_percent': 21, 'reset_at': '2099-01-01T00:00:00Z'}]},
            {'windows': [{'label': 'Weekly', 'used_percent': 42, 'reset_at': '2099-01-02T00:00:00Z'}]},
        ]}}}
        for mode in ('all', 'worst'):
            with self.subTest(mode=mode):
                tree = render(component='status', statusMode=mode, data=data)
                buttons = [n for n in nodes(tree) if n.get('type') == 'button']
                self.assertEqual(len(buttons), 1)
                tips = [n for n in nodes(tree) if n.get('type') == 'Tip']
                self.assertEqual(len(tips), 1)
                self.assertNotIn('title', buttons[0]['props'])
                self.assertTrue(buttons[0]['props'].get('aria-label'))
                self.assertEqual(text(buttons[0]).strip(), 'Quota')
                props = tips[0]['props']
                self.assertEqual(props['side'], 'top')
                self.assertEqual(props['align'], 'start')
                self.assertEqual(props['boundary'], 'viewport')
                style = props['label']['props']['style']
                self.assertEqual(style['whiteSpace'], 'normal')
                self.assertTrue(style['maxHeight'])
                self.assertEqual(style['overflowY'], 'auto')
                tip = tooltip_text(tree)
                self.assertLess(tip.index('Account 1'), tip.index('Account 2'))
                self.assertEqual(tip.count('79%'), 1)
                self.assertEqual(tip.count('58%'), 1)
                self.assertIn('2 accounts', tip)
                self.assertEqual(len(windows(props['label'])), 2)
