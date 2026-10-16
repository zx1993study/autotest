from app.models.resource_record import ResourceRecord


def resolve_app_connection(repository, task_id, node_key, transition):
    db = repository.db
    resource = transition['resource']
    if resource['table'] not in {'app_devices','app_entries'}:
        raise ValueError('Unsupported app connection resource')
    try:
        task = db.query(ResourceRecord).filter(ResourceRecord.table_name == 'agent_tasks',
            ResourceRecord.id == task_id, ResourceRecord.deleted.is_(False)).populate_existing().with_for_update().first()
        extra = dict(task.data_json or {}) if task else {}
        current = extra.get('data') or {}
        if not task or task.status != 'running' or current.get('claimed_by') != node_key or \
                any(current.get(k) != v for k,v in transition['expected'].items()):
            db.rollback()
            return None
        row = db.query(ResourceRecord).filter(ResourceRecord.table_name == resource['table'],
            ResourceRecord.id == resource['id'], ResourceRecord.deleted.is_(False)).populate_existing().with_for_update().first()
        row_extra = dict(row.data_json or {}) if row else {}
        data = row_extra.get('data') or {}
        if not row or row.status != 'active' or row.project_id != resource['project_id'] or row.name != resource.get('name', row.name) or \
                any(data.get(k) != v for k,v in resource['expected_data'].items()):
            db.rollback()
            return None
        row.data_json = {**row_extra, 'data':{**data, **resource['patch']}}
        task.data_json = {**extra, 'data':{**current, **transition['patch']}}
        db.commit()
        db.refresh(task)
        return repository._to_dict(task)
    except Exception:
        db.rollback()
        raise
