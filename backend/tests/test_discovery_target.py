import unittest

from web_automation.discovery.target import is_login_url, matches_target_page


class DiscoveryTargetTest(unittest.TestCase):
    def test_login_routes_and_hashes(self):
        for route in ('/login', '/login?redirect=/customers', 'https://example.test/#/login', '/auth/sign-in/', '/signin'):
            self.assertTrue(is_login_url(route), route)
        for route in ('/login-help', '/customers?redirect=/login', '/my-login', '/dashboard'):
            self.assertFalse(is_login_url(route), route)

    def test_target_route_not_last_redirect(self):
        target = 'https://example.test/login'
        self.assertTrue(matches_target_page(target, target + '/?redirect=/home'))
        self.assertFalse(matches_target_page(target, 'https://example.test/home'))
        self.assertFalse(matches_target_page(target, 'https://other.test/login'))
        self.assertFalse(matches_target_page(target, 'https://example.test/#/home'))
        self.assertFalse(matches_target_page('https://example.test/#/login', 'https://example.test/#/home'))
        self.assertTrue(matches_target_page('https://example.test:443/#/login', 'https://example.test/#/login/'))

    def test_explicit_query_values_cannot_change(self):
        self.assertFalse(matches_target_page('https://example.test/customer?id=1', 'https://example.test/customer?id=2'))
        self.assertFalse(matches_target_page('https://example.test/#/customer?id=1', 'https://example.test/#/customer?id=2'))
