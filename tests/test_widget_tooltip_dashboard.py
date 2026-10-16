"""Render the shipped hover dashboard, not a parallel tooltip model."""
import unittest
from widget_harness import render, nodes, tooltip_text, text

DATA = {
    'age_s': 0, 'fetched_at': '2026-10-13T17:00:00Z',
    'providers': {
        'anthropic': {'unavailable_reason': 'no-credentials', 'windows': []},
        'copilot': {'plan': 'Individual', 'windows': [{'label': 'Premium requests', 'used_percent': 12, 'reset_at': '2099-01-01T00:00:00Z'}]},
        'openai-codex': {'accounts': [
            {'label': 'Work', 'plan': 'Team', 'windows': [{'label': 'Session', 'used_percent': 48}, {'label': 'Weekly', 'used_percent': 25}]},
            {'label': 'Personal', 'plan': 'Plus', 'windows': [{'label': 'Session', 'used_percent': 17}, {'label': 'Weekly', 'used_percent': 65}]},
        ]},
        'deepseek': {'unavailable_reason': 'no-credentials'},
    },
}

class TooltipDashboardTests(unittest.TestCase):
    def test_dashboard_has_explicit_compact_layout_not_inherited_pre_wrap(self):
        tree = render(component='status', data=DATA)
        tip = next(n for n in nodes(tree) if n.get('type') == 'Tip')
        wrapper = tip['props']['label']['props']
        self.assertEqual(wrapper.get('style', {}).get('whiteSpace'), 'normal')
        dashboard = next(n for n in nodes(tip['props']['label']) if n['props'].get('data-quota-mini') is not None)
        self.assertEqual(dashboard['props']['style']['lineHeight'], '1.35')
        self.assertEqual(dashboard['props']['style']['display'], 'flex')

    def test_multiple_accounts_use_a_compact_responsive_grid(self):
        tree = render(component='status', data=DATA)
        label = next(n['props']['label'] for n in nodes(tree) if n.get('type') == 'Tip')
        grid = next((n for n in nodes(label) if n['props'].get('data-quota-mini-accounts') == 'openai-codex'), None)
        self.assertIsNotNone(grid, 'Codex accounts must share a responsive two-column group instead of tall repeated cards')
        self.assertEqual(grid['props']['style']['display'], 'grid')
        self.assertIn('auto-fit', grid['props']['style']['gridTemplateColumns'])
        self.assertEqual(len(grid['props']['children']), 2)

    def test_pending_refresh_is_reported_instead_of_permanent_cached_message(self):
        tree = render(component='status', data={**DATA, 'age_s': 180}, isFetching=True)
        self.assertIn('Refreshing', tooltip_text(tree))
        self.assertNotIn('awaiting refresh', tooltip_text(tree))

if __name__ == '__main__':
    unittest.main()
