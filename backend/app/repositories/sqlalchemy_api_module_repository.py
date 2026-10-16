from typing import Any

from sqlalchemy import func, or_

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository


class SqlAlchemyApiModuleRepository(SqlAlchemyResourceRepository):
    def save_module(self, project_id: int, item_id: int | None, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            self._lock_project(project_id)
            duplicate = self._modules(project_id).filter(func.lower(ResourceRecord.name) == payload["name"].lower())
            if item_id is not None:
                duplicate = duplicate.filter(ResourceRecord.id != item_id)
            if duplicate.first():
                self.db.rollback()
                return None
            if item_id is None:
                row = ResourceRecord(table_name="api_modules", project_id=project_id, name=payload["name"], status="active", data_json={"data": {"module_key": payload["name"], "is_ungrouped": False}})
                self.db.add(row)
            else:
                row = self._modules(project_id).filter(ResourceRecord.id == item_id).with_for_update().first()
                if row is None:
                    self.db.rollback()
                    return None
                references = self._references(row).with_for_update().all()
                for interface in references:
                    extra = dict(interface.data_json or {})
                    extra["data"] = {**extra.get("data", {}), "module_id": row.id, "module": payload["name"]}
                    interface.data_json = extra
                extra = dict(row.data_json or {})
                extra["data"] = {**extra.get("data", {}), "module_key": payload["name"]}
                row.data_json = extra
                row.name = payload["name"]
            row.description = payload.get("description")
            self.db.commit()
            self.db.refresh(row)
            return self._to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def module_reference_count(self, item_id: int) -> int:
        row = self.db.query(ResourceRecord).filter(ResourceRecord.id == item_id, ResourceRecord.table_name == "api_modules", ResourceRecord.deleted.is_(False)).first()
        return self._references(row).count() if row else 0

    def delete_module(self, project_id: int, item_id: int) -> bool:
        try:
            self._lock_project(project_id)
            row = self._modules(project_id).filter(ResourceRecord.id == item_id).with_for_update().first()
            if row is None or self._references(row).count():
                self.db.rollback()
                return False
            row.deleted = True
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _lock_project(self, project_id: int) -> None:
        self.db.query(ResourceRecord).filter(ResourceRecord.table_name == "projects", ResourceRecord.id == project_id, ResourceRecord.deleted.is_(False)).with_for_update().first()

    def _modules(self, project_id: int):
        return self.db.query(ResourceRecord).filter(ResourceRecord.table_name == "api_modules", ResourceRecord.project_id == project_id, ResourceRecord.deleted.is_(False))

    def _references(self, row: ResourceRecord):
        module_id = ResourceRecord.data_json["data"]["module_id"].as_integer()
        module_name = ResourceRecord.data_json["data"]["module"].as_string()
        return self.db.query(ResourceRecord).filter(
            ResourceRecord.table_name == "api_interfaces",
            ResourceRecord.project_id == row.project_id,
            ResourceRecord.deleted.is_(False),
            or_(module_id == row.id, (module_id.is_(None)) & (module_name == row.name)),
        )
