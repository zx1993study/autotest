from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.services.web_page_service import WebPageResourceService

PAGE_GROUP_TABLE = "web_page_groups"
PAGE_FEATURE_TABLE = "web_pages"
PAGE_API_RELATION_TABLE = "web_page_api_relations"


class WebPageManagementService:
    """Build a page directory without changing legacy Web feature identifiers."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def list_groups(
        self,
        project_id: int,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        groups, _ = self.repository.list(PAGE_GROUP_TABLE, project_id=project_id, page=1, page_size=10000)
        features, _ = self.repository.list(PAGE_FEATURE_TABLE, project_id=project_id, page=1, page_size=10000)
        relations, _ = self.repository.list(PAGE_API_RELATION_TABLE, project_id=project_id, page=1, page_size=10000)

        if self._requires_group_synchronization(features, groups):
            self.synchronize_project(project_id, features=features, groups=groups, relations=relations)
            groups, _ = self.repository.list(PAGE_GROUP_TABLE, project_id=project_id, page=1, page_size=10000)
            features, _ = self.repository.list(PAGE_FEATURE_TABLE, project_id=project_id, page=1, page_size=10000)
            relations, _ = self.repository.list(PAGE_API_RELATION_TABLE, project_id=project_id, page=1, page_size=10000)
        else:
            groups_by_key = self._groups_by_key(groups)
            created_relations = self._synchronize_recorded_relations(
                project_id,
                features,
                groups_by_key,
                relations,
            )
            if created_relations:
                relations, _ = self.repository.list(
                    PAGE_API_RELATION_TABLE,
                    project_id=project_id,
                    page=1,
                    page_size=10000,
                )

        feature_counts = Counter(self._int(self._data(item).get("page_group_id")) for item in features)
        relation_interfaces: dict[int, set[int]] = defaultdict(set)
        for relation in relations:
            data = self._data(relation)
            group_id = self._int(data.get("page_group_id"))
            interface_id = self._int(data.get("interface_id"))
            if group_id and interface_id:
                relation_interfaces[group_id].add(interface_id)

        normalized_keyword = str(keyword or "").strip().casefold()
        result = []
        for group in groups:
            if status and str(group.get("status") or "") != status:
                continue
            data = self._data(group)
            searchable = " ".join(
                str(value or "") for value in (group.get("name"), data.get("route"), data.get("url"))
            ).casefold()
            if normalized_keyword and normalized_keyword not in searchable:
                continue
            item = dict(group)
            item["feature_count"] = feature_counts.get(int(group["id"]), 0)
            item["interface_count"] = len(relation_interfaces.get(int(group["id"]), set()))
            result.append(item)

        result.sort(key=lambda item: (str(item.get("updated_at") or ""), int(item["id"])), reverse=True)
        total = len(result)
        start = (page - 1) * page_size
        return result[start : start + page_size], total

    def get_group(self, group_id: int) -> dict[str, Any]:
        group = self._required_group(group_id)
        project_id = self._int(group.get("project_id"))
        features, _ = self.repository.list(
            PAGE_FEATURE_TABLE,
            project_id=project_id,
            page=1,
            page_size=10000,
            data_filters={"page_group_id": group_id},
        )
        relations, _ = self.repository.list(
            PAGE_API_RELATION_TABLE,
            project_id=project_id,
            page=1,
            page_size=10000,
            data_filters={"page_group_id": group_id},
        )
        item = dict(group)
        item["feature_count"] = len(features)
        item["interface_count"] = len(
            {self._int(self._data(relation).get("interface_id")) for relation in relations}
            - {None}
        )
        return item

    def create_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = self._int(payload.get("project_id"))
        if not project_id:
            raise BusinessRuleError("请选择页面所属项目")
        route, url = self._normalized_location(payload.get("route"), payload.get("url"))
        if not route:
            raise BusinessRuleError("页面路由或页面地址不能为空")
        self.synchronize_project(project_id)
        self._ensure_unique_page_key(project_id, route)

        data = {
            "page_key": self._page_key(route),
            "route": route,
            "url": url,
            "url_variants": [url] if url else [],
        }
        if payload.get("auth_id") is not None:
            data["auth_id"] = payload["auth_id"]
        group = self.repository.create(
            PAGE_GROUP_TABLE,
            {
                "name": str(payload.get("name") or "").strip(),
                "project_id": project_id,
                "description": payload.get("description"),
                "status": str(payload.get("status") or "active"),
                "data": data,
            },
        )
        feature = WebPageResourceService(self.repository).create(
            {
                "name": group["name"],
                "project_id": project_id,
                "description": payload.get("description"),
                "status": str(payload.get("status") or "active"),
                "data": {
                    "page_group_id": int(group["id"]),
                    "route": route,
                    "url": url,
                    "feature_type": "page",
                    "auth_id": payload.get("auth_id"),
                },
            }
        )
        group_data = {**self._data(group), "canonical_feature_id": int(feature["id"])}
        updated = self.repository.update(PAGE_GROUP_TABLE, int(group["id"]), {"data": group_data}) or group
        updated["feature_count"] = 1
        updated["interface_count"] = 0
        return updated

    def update_group(self, group_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        group = self._required_group(group_id)
        current_data = self._data(group)
        route_value = payload.get("route") if "route" in payload else current_data.get("route")
        url_value = payload.get("url") if "url" in payload else current_data.get("url")
        route, url = self._normalized_location(route_value, url_value)
        if not route:
            raise BusinessRuleError("页面路由或页面地址不能为空")
        project_id = int(group["project_id"])
        self._ensure_unique_page_key(project_id, route, exclude_group_id=group_id)

        next_data = {
            **current_data,
            "page_key": self._page_key(route),
            "route": route,
            "url": url,
        }
        if "auth_id" in payload:
            if payload.get("auth_id") is None:
                next_data.pop("auth_id", None)
            else:
                next_data["auth_id"] = payload["auth_id"]
        update_payload = {key: value for key, value in payload.items() if key in {"name", "description", "status"}}
        update_payload["data"] = next_data
        updated = self.repository.update(PAGE_GROUP_TABLE, group_id, update_payload)
        if not updated:
            raise ResourceNotFoundError("Web 页面不存在")
        self._propagate_group_location(updated)
        return self.get_group(group_id)

    def list_features(
        self,
        group_id: int,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
        feature_type: str | None = None,
        script_status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        group = self._required_group(group_id)
        project_id = int(group["project_id"])
        filters = {"page_group_id": group_id, "status": status, "feature_type": feature_type, "script_status": script_status}
        filters = {key: value for key, value in filters.items() if value is not None and value != ""}
        rows, total = self.repository.list(
            PAGE_FEATURE_TABLE,
            keyword=keyword,
            project_id=project_id,
            page=page,
            page_size=page_size,
            data_filters=filters,
        )
        counts = self.repository.web_feature_counts([int(row["id"]) for row in rows]) if rows else {}
        result = []
        for row in rows:
            item = dict(row)
            feature_id = int(row["id"])
            item.update(counts[feature_id])
            data = self._data(row)
            item["parameter_count"] = len(data.get("parameters") or [])
            item["script_status"] = data.get("script_status") or ("legacy" if item["case_count"] else "missing")
            result.append(item)
        return result, total

    def list_interfaces(
        self,
        group_id: int,
        feature_id: int | None,
        keyword: str | None,
        method: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        group = self._required_group(group_id)
        project_id = int(group["project_id"])
        feature_names = self._feature_names(group_id, project_id)
        if feature_id and feature_id not in feature_names:
            raise BusinessRuleError("所选页面功能不属于当前页面")
        relations, _ = self.repository.list(
            PAGE_API_RELATION_TABLE,
            project_id=project_id,
            page=1,
            page_size=10000,
            data_filters={"page_group_id": group_id},
        )
        if feature_id:
            relations = [
                item
                for item in relations
                if self._int(self._data(item).get("feature_id")) in {None, feature_id}
            ]
        interfaces, _ = self.repository.list("api_interfaces", project_id=project_id, page=1, page_size=10000)
        interfaces_by_id = {int(item["id"]): item for item in interfaces}
        normalized_keyword = str(keyword or "").strip().casefold()
        normalized_method = str(method or "").strip().upper()
        result = []
        for relation in relations:
            relation_data = self._data(relation)
            interface = interfaces_by_id.get(self._int(relation_data.get("interface_id")) or 0)
            if not interface:
                continue
            interface_data = self._data(interface)
            interface_method = str(interface_data.get("method") or "").upper()
            searchable = " ".join(
                str(value or "")
                for value in (interface.get("name"), interface_data.get("path"), interface_data.get("module"))
            ).casefold()
            if normalized_keyword and normalized_keyword not in searchable:
                continue
            if normalized_method and interface_method != normalized_method:
                continue
            relation_feature_id = self._int(relation_data.get("feature_id"))
            result.append(
                {
                    **interface,
                    "relation_id": int(relation["id"]),
                    "relation_source": relation_data.get("source") or "manual",
                    "relation_feature_id": relation_feature_id,
                    "relation_feature_name": feature_names.get(relation_feature_id) if relation_feature_id else None,
                }
            )
        result.sort(key=lambda item: (str(self._data(item).get("path") or ""), int(item["id"])))
        total = len(result)
        start = (page - 1) * page_size
        return result[start : start + page_size], total

    def create_relations(
        self,
        group_id: int,
        interface_ids: list[int],
        feature_id: int | None,
        source: str,
    ) -> dict[str, Any]:
        group = self._required_group(group_id)
        project_id = int(group["project_id"])
        feature_names = self._feature_names(group_id, project_id)
        if feature_id and feature_id not in feature_names:
            raise BusinessRuleError("所选页面功能不属于当前页面")
        interfaces, _ = self.repository.list("api_interfaces", project_id=project_id, page=1, page_size=10000)
        interfaces_by_id = {int(item["id"]): item for item in interfaces}
        requested_ids = list(dict.fromkeys(int(item_id) for item_id in interface_ids))
        missing_ids = [item_id for item_id in requested_ids if item_id not in interfaces_by_id]
        if missing_ids:
            raise BusinessRuleError("部分 API 不存在或不属于当前项目", {"interface_ids": missing_ids})

        existing, _ = self.repository.list(
            PAGE_API_RELATION_TABLE,
            project_id=project_id,
            page=1,
            page_size=10000,
            data_filters={"page_group_id": group_id},
        )
        existing_keys = {
            (self._int(self._data(item).get("interface_id")), self._int(self._data(item).get("feature_id")))
            for item in existing
        }
        rows = []
        for interface_id in requested_ids:
            if (interface_id, feature_id) in existing_keys:
                continue
            interface = interfaces_by_id[interface_id]
            rows.append(
                {
                    "name": f"{group['name']} / {interface['name']}",
                    "project_id": project_id,
                    "status": "active",
                    "data": {
                        "page_group_id": group_id,
                        "feature_id": feature_id,
                        "interface_id": interface_id,
                        "source": source,
                    },
                }
            )
        created = self.repository.create_many(PAGE_API_RELATION_TABLE, rows)
        return {"created_count": len(created), "skipped_count": len(requested_ids) - len(created), "items": created}

    def delete_relation(self, group_id: int, relation_id: int) -> bool:
        self._required_group(group_id)
        relation = self.repository.get(PAGE_API_RELATION_TABLE, relation_id)
        if not relation or self._int(self._data(relation).get("page_group_id")) != group_id:
            raise ResourceNotFoundError("页面 API 关联不存在")
        if not self.repository.delete(PAGE_API_RELATION_TABLE, relation_id):
            raise ResourceNotFoundError("页面 API 关联不存在")
        return True

    def synchronize_project(
        self,
        project_id: int,
        *,
        features: list[dict[str, Any]] | None = None,
        groups: list[dict[str, Any]] | None = None,
        relations: list[dict[str, Any]] | None = None,
    ) -> dict[str, int]:
        if features is None:
            features, _ = self.repository.list(PAGE_FEATURE_TABLE, project_id=project_id, page=1, page_size=10000)
        if groups is None:
            groups, _ = self.repository.list(PAGE_GROUP_TABLE, project_id=project_id, page=1, page_size=10000)
        groups_by_key = self._groups_by_key(groups)
        grouped_features: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for feature in features:
            data = self._data(feature)
            route, _ = self._normalized_location(data.get("route"), data.get("url"))
            if route:
                grouped_features[self._page_key(route)].append(feature)

        created_count = 0
        updated_count = 0
        feature_updates: list[tuple[int, dict[str, Any]]] = []
        for page_key, page_features in grouped_features.items():
            primary = self._primary_feature(page_features)
            route, _ = self._normalized_location(self._data(primary).get("route"), self._data(primary).get("url"))
            urls = self._url_variants(page_features)
            primary_url = self._primary_url(urls)
            group = groups_by_key.get(page_key)
            if group is None:
                primary_data = self._data(primary)
                group_data: dict[str, Any] = {
                    "page_key": page_key,
                    "route": route,
                    "url": primary_url,
                    "url_variants": urls,
                    "canonical_feature_id": int(primary["id"]),
                }
                if primary_data.get("auth_id") not in (None, ""):
                    group_data["auth_id"] = primary_data["auth_id"]
                group = self.repository.create(
                    PAGE_GROUP_TABLE,
                    {
                        "name": primary.get("name") or route,
                        "project_id": project_id,
                        "description": primary.get("description"),
                        "status": primary.get("status") or "active",
                        "data": group_data,
                    },
                )
                groups_by_key[page_key] = group
                created_count += 1
            else:
                current_data = self._data(group)
                next_data = {
                    **current_data,
                    "page_key": page_key,
                    "route": current_data.get("route") or route,
                    "url": current_data.get("url") or primary_url,
                    "url_variants": urls,
                    "canonical_feature_id": current_data.get("canonical_feature_id") or int(primary["id"]),
                }
                if next_data != current_data:
                    group = self.repository.update(PAGE_GROUP_TABLE, int(group["id"]), {"data": next_data}) or group
                    groups_by_key[page_key] = group
                    updated_count += 1

            group_id = int(group["id"])
            for feature in page_features:
                data = self._data(feature)
                if self._int(data.get("page_group_id")) == group_id:
                    continue
                feature_updates.append((int(feature["id"]), {"data": {**data, "page_group_id": group_id}}))

        if feature_updates:
            self.repository.update_many(PAGE_FEATURE_TABLE, feature_updates)
        created_relations = self._synchronize_recorded_relations(
            project_id,
            features,
            groups_by_key,
            relations,
        )
        return {
            "created_groups": created_count,
            "updated_groups": updated_count,
            "linked_features": len(feature_updates),
            "linked_interfaces": created_relations,
        }

    def _synchronize_recorded_relations(
        self,
        project_id: int,
        features: list[dict[str, Any]],
        groups_by_key: dict[str, dict[str, Any]],
        existing_relations: list[dict[str, Any]] | None = None,
    ) -> int:
        candidates: set[tuple[int, int]] = set()
        for feature in features:
            data = self._data(feature)
            ids = data.get("related_interface_ids")
            if not isinstance(ids, list):
                continue
            route, _ = self._normalized_location(data.get("route"), data.get("url"))
            group = groups_by_key.get(self._page_key(route)) if route else None
            if not group:
                continue
            group_id = int(group["id"])
            candidates.update(
                (group_id, item_id)
                for item_id in (self._int(value) for value in ids)
                if item_id
            )
        if not candidates:
            return 0

        if existing_relations is None:
            existing_relations, _ = self.repository.list(
                PAGE_API_RELATION_TABLE,
                project_id=project_id,
                page=1,
                page_size=10000,
            )
        existing_keys = {
            (
                self._int(self._data(item).get("page_group_id")),
                self._int(self._data(item).get("interface_id")),
            )
            for item in existing_relations
            if self._int(self._data(item).get("feature_id")) is None
        }
        missing_candidates = candidates - existing_keys
        if not missing_candidates:
            return 0

        valid_interfaces, _ = self.repository.list(
            "api_interfaces",
            project_id=project_id,
            page=1,
            page_size=10000,
        )
        valid_ids = {int(item["id"]) for item in valid_interfaces}
        groups_by_id = {int(group["id"]): group for group in groups_by_key.values()}
        rows = []
        for group_id, interface_id in sorted(missing_candidates):
            group = groups_by_id.get(group_id)
            if not group or interface_id not in valid_ids:
                continue
            interface = next(item for item in valid_interfaces if int(item["id"]) == interface_id)
            rows.append(
                {
                    "name": f"{group['name']} / {interface['name']}",
                    "project_id": project_id,
                    "status": "active",
                    "data": {
                        "page_group_id": group_id,
                        "feature_id": None,
                        "interface_id": interface_id,
                        "source": "network",
                    },
                }
            )
        return len(self.repository.create_many(PAGE_API_RELATION_TABLE, rows))

    def _requires_group_synchronization(
        self,
        features: list[dict[str, Any]],
        groups: list[dict[str, Any]],
    ) -> bool:
        groups_by_key = self._groups_by_key(groups)
        grouped_features: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for feature in features:
            data = self._data(feature)
            route, _ = self._normalized_location(data.get("route"), data.get("url"))
            if not route:
                continue
            page_key = self._page_key(route)
            group = groups_by_key.get(page_key)
            if not group or self._int(data.get("page_group_id")) != int(group["id"]):
                return True
            grouped_features[page_key].append(feature)

        for page_key, page_features in grouped_features.items():
            group = groups_by_key[page_key]
            if self._data(group).get("url_variants") != self._url_variants(page_features):
                return True
        return False

    def _groups_by_key(self, groups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            str(self._data(group).get("page_key") or self._page_key(self._data(group).get("route"))): group
            for group in groups
        }

    def _propagate_group_location(self, group: dict[str, Any]) -> None:
        group_id = int(group["id"])
        data = self._data(group)
        features, _ = self.repository.list(
            PAGE_FEATURE_TABLE,
            project_id=int(group["project_id"]),
            page=1,
            page_size=10000,
            data_filters={"page_group_id": group_id},
        )
        updates = []
        for feature in features:
            feature_data = {**self._data(feature), "route": data.get("route"), "url": data.get("url")}
            if "auth_id" in data:
                feature_data["auth_id"] = data["auth_id"]
            updates.append((int(feature["id"]), {"data": feature_data}))
        if updates:
            self.repository.update_many(PAGE_FEATURE_TABLE, updates)

    def _ensure_unique_page_key(self, project_id: int, route: str, exclude_group_id: int | None = None) -> None:
        groups, _ = self.repository.list(PAGE_GROUP_TABLE, project_id=project_id, page=1, page_size=10000)
        page_key = self._page_key(route)
        if any(
            int(item["id"]) != exclude_group_id
            and str(
                self._data(item).get("page_key")
                or self._page_key(self._data(item).get("route"))
            ) == page_key
            for item in groups
        ):
            raise BusinessRuleError("当前项目已存在相同路由的页面")

    def _feature_names(self, group_id: int, project_id: int) -> dict[int, str]:
        rows, _ = self.repository.list(
            PAGE_FEATURE_TABLE,
            project_id=project_id,
            page=1,
            page_size=10000,
            data_filters={"page_group_id": group_id},
        )
        return {int(item["id"]): str(item.get("name") or "") for item in rows}

    def _required_group(self, group_id: int) -> dict[str, Any]:
        group = self.repository.get(PAGE_GROUP_TABLE, group_id)
        if not group:
            raise ResourceNotFoundError("Web 页面不存在")
        return group

    def _primary_feature(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        return sorted(
            features,
            key=lambda item: (
                self._data(item).get("feature_type") != "page",
                not str(item.get("name") or "").endswith("页面"),
                int(item["id"]),
            ),
        )[0]

    def _url_variants(self, features: list[dict[str, Any]]) -> list[str]:
        result = []
        for feature in features:
            data = self._data(feature)
            for value in (data.get("url"), data.get("route")):
                text = str(value or "").strip()
                if text.startswith(("http://", "https://")) and text not in result:
                    result.append(text)
        return sorted(result, key=lambda value: ("?" in value, len(value), value))[:50]

    def _primary_url(self, urls: list[str]) -> str:
        return urls[0] if urls else ""

    def _normalized_location(self, route_value: Any, url_value: Any) -> tuple[str, str]:
        raw_route = str(route_value or "").strip()
        raw_url = str(url_value or "").strip()
        route_source = raw_route or raw_url
        if not route_source:
            return "", raw_url
        parsed = urlsplit(route_source)
        path = parsed.path or "/"
        if not path.startswith("/"):
            path = f"/{path}"
        route = path.rstrip("/") or "/"
        url = raw_url
        if not url and parsed.scheme and parsed.netloc:
            url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
        return route, url

    def _page_key(self, route: Any) -> str:
        return str(route or "").strip().rstrip("/").casefold() or "/"

    @staticmethod
    def _data(item: dict[str, Any]) -> dict[str, Any]:
        value = item.get("data")
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _int(value: Any) -> int | None:
        try:
            result = int(value)
        except (TypeError, ValueError):
            return None
        return result if result > 0 else None
