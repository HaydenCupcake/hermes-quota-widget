"""Sidebar nav visibility: off by default, toggleable via settings, persisted."""
import unittest
from widget_harness import render


def registrations(**options):
    return render(component='registrations', **options)


def ids(regs):
    return {r.get('id') for r in regs}


class SidebarNavToggleTests(unittest.TestCase):
    def test_sidebar_nav_absent_by_default(self):
        self.assertNotIn('nav', ids(registrations()),
                         'Quota must not appear in the left sidebar unless the user opts in')

    def test_statusbar_and_route_still_registered_by_default(self):
        present = ids(registrations())
        self.assertIn('statusbar', present)
        self.assertIn('page', present,
                      'The /quota route must stay registered so the nav can be turned back on')

    def test_sidebar_nav_present_when_setting_enabled(self):
        self.assertIn('nav', ids(registrations(storage={'showSidebarNav': True})),
                      'Sidebar nav must register when showSidebarNav is true')

    def test_nav_points_at_quota_route(self):
        regs = registrations(storage={'showSidebarNav': True})
        nav = next(r for r in regs if r.get('id') == 'nav')
        self.assertEqual(nav['data']['path'], '/quota')


if __name__ == '__main__':
    unittest.main()
