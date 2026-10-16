import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository


class AppConnectionRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.repo = SqlAlchemyResourceRepository(self.session)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.entry = self.repo.create('app_entries', {'name':'App','project_id':1,
            'data':{'bundle_id':None,'no_reset':True}})
        self.task = self.repo.create('agent_tasks', {'name':'Synthetic','status':'running',
            'data':{'claimed_by':'node','live':{'phase':'connecting'},'payload':{'bundle_id':''}}})
        self.transition = {'expected':{'live':{'phase':'connecting'},'payload':{'bundle_id':''}},
            'patch':{'live':{'phase':'observing'},'payload':{'bundle_id':'test.real.app'}},
            'resource':{'table':'app_entries','id':self.entry['id'],'project_id':1,'name':'App',
                'expected_data':{'bundle_id':None},'patch':{'bundle_id':'test.real.app'}}}

    def resolve(self):
        return self.repo.resolve_app_connection(self.task['id'],'node',self.transition)

    def test_task_and_entry_updated_together_other_data_preserved(self):
        self.assertEqual('observing',self.resolve()['data']['live']['phase'])
        data = self.repo.get('app_entries',self.entry['id'])['data']
        self.assertEqual('test.real.app',data['bundle_id'])
        self.assertTrue(data['no_reset'])

    def test_concurrent_bundle_change_does_not_update_task(self):
        self.repo.update('app_entries',self.entry['id'],{'data':{'bundle_id':'test.other.app'}})
        self.assertIsNone(self.resolve())
        self.assertEqual('connecting',self.repo.get('agent_tasks',self.task['id'])['data']['live']['phase'])

    def test_cancel_and_wrong_node_do_not_write_identity(self):
        self.assertIsNone(self.repo.resolve_app_connection(self.task['id'],'other-node',self.transition))
        self.repo.update('agent_tasks',self.task['id'],{'status':'canceled'})
        self.assertIsNone(self.resolve())
        self.assertIsNone(self.repo.get('app_entries',self.entry['id'])['data']['bundle_id'])

    def test_commit_error_rolls_back_both_rows(self):
        with patch.object(self.session,'commit',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.resolve()
        self.assertIsNone(self.repo.get('app_entries',self.entry['id'])['data']['bundle_id'])
        self.assertEqual('connecting',self.repo.get('agent_tasks',self.task['id'])['data']['live']['phase'])
