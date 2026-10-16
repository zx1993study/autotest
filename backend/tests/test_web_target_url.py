import unittest
from unittest.mock import Mock

from app.services.web_target_url_service import resolve_web_target_url


class WebTargetUrlTest(unittest.TestCase):
    def test_root_url_does_not_override_explicit_history_route(self):
        repo = Mock()
        repo.list.return_value = ([], 0)
        page = {'project_id': 1, 'data': {'url': 'https://example.test/', 'route': '/login'}}
        self.assertEqual(resolve_web_target_url(repo, page), 'https://example.test/login')

    def test_hash_routing_is_inferred_only_from_same_site_saved_pages(self):
        repo = Mock()
        repo.list.return_value = ([{'data': {'url': 'https://example.test/#/order/take'}}], 1)
        page = {'project_id': 1, 'data': {'url': 'https://example.test/', 'route': '/login'}}
        self.assertEqual(resolve_web_target_url(repo, page), 'https://example.test/#/login')
        repo.list.return_value = ([{'data': {'url': 'https://other.test/#/order/take'}}], 1)
        self.assertEqual(resolve_web_target_url(repo, page), 'https://example.test/login')

    def test_full_url_and_explicit_override_are_preserved(self):
        repo = Mock()
        page = {'project_id': 1, 'data': {'url': 'https://example.test/#/login?redirect=home', 'route': '/login'}}
        self.assertEqual(resolve_web_target_url(repo, page), page['data']['url'])
        self.assertEqual(resolve_web_target_url(repo, page, 'https://example.test/'), 'https://example.test/')
        repo.list.assert_not_called()
