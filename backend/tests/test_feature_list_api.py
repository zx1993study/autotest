import unittest
from unittest.mock import Mock

from app.api.v1.web_page_management import get_web_page_management_service, router
from app.services.web_page_management_service import WebPageManagementService
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FeatureListApiTest(unittest.TestCase):
    def setUp(self):
        self.service = Mock(spec=WebPageManagementService)
        self.service.list_features.return_value = ([], 31)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_web_page_management_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_filters_and_page_size_alias_reach_service(self):
        response = self.client.get('/web-testing/page-groups/1/features', params={
            'keyword': 'Item', 'feature_type': 'query', 'script_status': 'missing',
            'status': 'active', 'page': 2, 'pageSize': 10,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'], {'items': [], 'total': 31, 'page': 2, 'pageSize': 10})
        self.service.list_features.assert_called_once_with(1, 'Item', 'active', 2, 10,
                                                           feature_type='query', script_status='missing')

    def test_invalid_pagination_and_filter_length_are_rejected_before_query(self):
        for params in ({'page': 0}, {'pageSize': 201}, {'feature_type': 'x' * 65}):
            with self.subTest(params=params):
                response = self.client.get('/web-testing/page-groups/1/features', params=params)
                self.assertEqual(response.status_code, 422)
        self.service.list_features.assert_not_called()


if __name__ == '__main__':
    unittest.main()
