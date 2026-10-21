from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_resource_repository
from app.api.v1.web_features import router
from app.db.base import Base
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.web_execution_summary import WebExecutionSummaryQuery
from app.services.web_execution_summary_service import WebExecutionSummaryService


@pytest.fixture
def setup_summary():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = SqlAlchemyResourceRepository(session)
        feature = repo.create('web_pages', {'name': 'Feature', 'project_id': 1, 'data': {'page_group_id': 300}})
        cases = [repo.create('web_test_cases', {'name': f'Case {i}', 'project_id': 1, 'source_id': feature['id']})
                 for i in range(3)]
        yield repo, feature, cases
    engine.dispose()


def record(repo, case_id, status='success', at=None, project_id=1, case_type='WEB', deleted=False, **data):
    row = ResourceRecord(table_name='execution_records', name='Run', status=status, project_id=project_id,
                         data_json={'data': {'case_id': case_id, 'case_type': case_type, **data}},
                         created_at=at or datetime(2026, 10, 21, 12), deleted=deleted)
    repo.db.add(row)
    repo.db.commit()
    return row


def summaries(repo, scope, ids):
    query = WebExecutionSummaryQuery(project_id=1, scope=scope, ids=ids)
    return {item.id: item for item in WebExecutionSummaryService(repo).summarize(query).items}


def test_latest_per_case_prevents_new_success_from_hiding_other_failure(setup_summary):
    repo, feature, cases = setup_summary
    earlier = datetime(2026, 10, 20, 12)
    failure = record(repo, cases[0]['id'], status='failed', at=earlier)
    record(repo, cases[1]['id'], business_result='passed', assertion_count=2)
    result = summaries(repo, 'feature', [feature['id']])[feature['id']]
    assert result.status == 'failed'
    assert (result.success_count, result.failed_count, result.not_run_count) == (1, 1, 1)
    assert result.record_id == failure.id
    assert result.executed_at == datetime(2026, 10, 21, 12)
    page = summaries(repo, 'page', [300])[300]
    assert page.model_dump(exclude={'id'}) == result.model_dump(exclude={'id'})


def test_latest_creation_time_and_id_ignore_edit_time_deleted_and_other_domains(setup_summary):
    repo, _, cases = setup_summary
    case_id = cases[0]['id']
    failure = record(repo, case_id, status='failed')
    old = record(repo, case_id, at=datetime(2026, 10, 20), business_result='passed', assertion_count=1)
    old.updated_at = datetime(2026, 10, 22)
    repo.db.commit()
    for overrides in ({'project_id': 2}, {'case_type': 'API'}, {'deleted': True}):
        record(repo, case_id, at=datetime(2026, 10, 22), **overrides)
    assert summaries(repo, 'case', [case_id])[case_id].record_id == failure.id
    latest = record(repo, case_id, business_result='passed', assertion_count=1)
    result = summaries(repo, 'case', [case_id])[case_id]
    assert result.status == 'success' and result.record_id == latest.id


def test_partial_unverified_and_unexecuted_never_become_success(setup_summary):
    repo, feature, cases = setup_summary
    assert summaries(repo, 'feature', [feature['id']])[feature['id']].status == 'not_run'
    record(repo, cases[0]['id'], business_result='passed', assertion_count=1)
    assert summaries(repo, 'feature', [feature['id']])[feature['id']].status == 'partial'
    record(repo, cases[1]['id'])
    record(repo, cases[2]['id'], business_result='passed', assertion_count=0)
    result = summaries(repo, 'feature', [feature['id']])[feature['id']]
    assert result.status == 'partial' and result.unverified_count == 2
    for case in cases[1:]:
        record(repo, case['id'], business_result='passed', assertion_count=1)
    assert summaries(repo, 'feature', [feature['id']])[feature['id']].status == 'success'


@pytest.mark.parametrize('status,expected', [('running', 'running'), ('queued', 'running'),
                                          ('canceled', 'canceled'), ('skipped', 'canceled'),
                                          ('error', 'failed'), ('success', 'unverified')])
def test_nonterminal_and_legacy_case_statuses(setup_summary, status, expected):
    repo, _, cases = setup_summary
    record(repo, cases[0]['id'], status=status)
    assert summaries(repo, 'case', [cases[0]['id']])[cases[0]['id']].status == expected


def test_deleted_cases_features_and_other_projects_are_excluded(setup_summary):
    repo, feature, cases = setup_summary
    repo.delete('web_test_cases', cases[0]['id'])
    other_feature = repo.create('web_pages', {'name': 'Other', 'project_id': 2, 'data': {'page_group_id': 300}})
    repo.create('web_test_cases', {'name': 'Foreign case', 'project_id': 2, 'source_id': feature['id']})
    result = summaries(repo, 'feature', [feature['id'], other_feature['id']])
    assert result[feature['id']].total_count == 2
    assert result[other_feature['id']].total_count == 0
    repo.delete('web_pages', feature['id'])
    assert summaries(repo, 'page', [300])[300].status == 'empty'


def test_one_lightweight_query_for_whole_batch_and_no_history_payload(setup_summary):
    repo, feature, cases = setup_summary
    for i in range(30):
        record(repo, cases[i % 3]['id'], at=datetime(2026, 10, 20) + timedelta(seconds=i),
               business_result='passed', assertion_count=1, screenshots=['private-large-image'],
               steps=['large-script-body'], secret_inputs={'password': 'not-for-list'})
    statements = []
    def capture(_connection, _cursor, statement, *_args):
        statements.append(statement)
    event.listen(repo.db.get_bind(), 'before_cursor_execute', capture)
    try:
        result = summaries(repo, 'feature', [feature['id'], 800, 801])
    finally:
        event.remove(repo.db.get_bind(), 'before_cursor_execute', capture)
    assert len(statements) == 1
    assert result[feature['id']].total_count == 3
    serialized = str([item.model_dump() for item in result.values()])
    assert 'private-large-image' not in serialized and 'not-for-list' not in serialized
    assert 'screenshots' not in statements[0] and 'steps' not in statements[0]


def test_batch_api_and_validation(setup_summary):
    repo, feature, _ = setup_summary
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    app.dependency_overrides[get_resource_repository] = lambda: repo
    with TestClient(app) as client:
        body = {'project_id': 1, 'scope': 'feature', 'ids': [feature['id']]}
        response = client.post('/api/v1/web-testing/execution-summaries', json=body)
        assert response.status_code == 200
        assert response.json()['data']['items'][0]['status'] == 'not_run'
        for patch in ({'scope': 'invalid'}, {'ids': []}, {'ids': [0]}, {'ids': list(range(1, 202))}):
            assert client.post('/api/v1/web-testing/execution-summaries', json={**body, **patch}).status_code == 422
