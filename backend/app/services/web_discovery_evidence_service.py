"""Persist capture evidence before model-dependent parameter/script validation."""
from app.schemas.web_features import WebInputParameter
from app.services.web_page_management_service import WebPageManagementService
from app.services.web_page_service import WebPageResourceService


class WebDiscoveryEvidenceService:
    def __init__(self, repository):
        self.repository = repository

    def attach(self, page, name, screenshot, dom=None):
        if not (page.get("data") or {}).get("page_group_id"):
            WebPageManagementService(self.repository).synchronize_project(page["project_id"])
            page = self.repository.get("web_pages", page["id"])
        group_id = page["data"]["page_group_id"]
        rows, _ = self.repository.list("web_pages", project_id=page["project_id"], page_size=10000, data_filters={"page_group_id": group_id})
        feature = next((r for r in rows if r["name"] == name and (r.get("data") or {}).get("feature_type") != "page"), None)
        if not feature:
            from app.services.web_feature_testing_service import (
                WebFeatureTestingService,
            )

            feature = WebFeatureTestingService(self.repository).save_feature(group_id, {"name": name, "feature_type": "login" if "登录" in name else "other"})
        data = dict(feature.get("data") or {})
        data["discovery_screenshots"] = [screenshot]
        if not data.get("script_version"):
            data["screenshots"] = [screenshot]
        if dom is not None:
            from web_automation.discovery.dom import safe_dom

            data["dom_snapshot"] = safe_dom(dom)
        WebPageResourceService(self.repository).update(feature["id"], {"data": data})
        return self.repository.get("web_pages", feature["id"])


def discovery_parameters(parameters):
    normalized = []
    for parameter in parameters:
        value = dict(parameter)
        if value.get("required") is None:
            value.update(required=False, required_known=False, confirmed=False)
        for key, empty in (("condition", {}), ("validation", {}), ("options", [])):
            if value.get(key) is None:
                value[key] = empty
        normalized.append(WebInputParameter.model_validate(value).model_dump())
    return normalized
