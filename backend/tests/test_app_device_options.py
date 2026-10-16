import unittest

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.app_device import DeviceOptionsQuery
from app.services.app_device_option_service import AppDeviceOptionService
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class AppDeviceOptionsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        ResourceRecord.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.service = AppDeviceOptionService(self.repo)
        self.first = self.repo.create('app_devices', {'name': 'Online phone', 'project_id': 1, 'data': {'connection_status': 'online'}})
        self.second = self.repo.create('app_devices', {'name': 'Offline tablet', 'project_id': 2, 'data': {'connection_status': 'offline'}})

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_pool_reuses_devices_without_rebinding_projects(self):
        options = self.service.list_options(DeviceOptionsQuery(project_id=3, scope='pool'))
        self.assertEqual({r['id'] for r in options}, {self.first['id'], self.second['id']})
        self.assertEqual(self.repo.get('app_devices', self.first['id'])['project_id'], 1)
        self.assertEqual(self.repo.get('app_devices', self.second['id'])['project_id'], 2)

    def test_project_mode_remains_scoped(self):
        options = self.service.list_options(DeviceOptionsQuery(project_id=1))
        self.assertEqual([r['id'] for r in options], [self.first['id']])

    def test_deleted_devices_not_returned_and_scope_validated(self):
        self.repo.delete('app_devices', self.first['id'])
        self.assertEqual(len(self.service.list_options(DeviceOptionsQuery(scope='pool'))), 1)
        with self.assertRaises(ValidationError):
            DeviceOptionsQuery(scope='invalid')
