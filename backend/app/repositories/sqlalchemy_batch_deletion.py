"""Set-based soft deletion with bounded statements and one transaction."""
from collections.abc import Iterator

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from app.models.resource_record import ResourceRecord

ID_BATCH_SIZE = 500


def id_batches(ids: list[int]) -> Iterator[list[int]]:
    unique = sorted(set(ids))
    for start in range(0, len(unique), ID_BATCH_SIZE):
        yield unique[start:start + ID_BATCH_SIZE]


def related_id_filter(parent_key: str, ids: list[int]):
    value = ResourceRecord.data_json["data"][parent_key].as_string()
    return cast(value, String).in_([str(item_id) for item_id in ids])


def soft_delete_ids(db: Session, model, ids: list[int], scope: tuple = ()) -> int:
    if not ids:
        return 0
    try:
        count = sum(db.query(model).filter(
            model.id.in_(batch), model.deleted.is_(False), *scope,
        ).update({model.deleted: True}, synchronize_session=False) for batch in id_batches(ids))
        db.commit()
        return int(count)
    except Exception:
        db.rollback()
        raise


def soft_delete_with_children(db: Session, table: str, ids: list[int], child_table: str, parent_key: str) -> int:
    if not ids:
        return 0
    try:
        active_ids = [row.id for batch in id_batches(ids) for row in db.query(ResourceRecord.id).filter(
            ResourceRecord.table_name == table, ResourceRecord.id.in_(batch),
            ResourceRecord.deleted.is_(False),
        ).with_for_update().all()]
        count = 0
        for batch in id_batches(active_ids):
            db.query(ResourceRecord).filter(
                ResourceRecord.table_name == child_table, ResourceRecord.deleted.is_(False),
                related_id_filter(parent_key, batch),
            ).update({ResourceRecord.deleted: True}, synchronize_session=False)
            count += db.query(ResourceRecord).filter(
                ResourceRecord.table_name == table, ResourceRecord.id.in_(batch),
                ResourceRecord.deleted.is_(False),
            ).update({ResourceRecord.deleted: True}, synchronize_session=False)
        db.commit()
        return int(count)
    except Exception:
        db.rollback()
        raise
