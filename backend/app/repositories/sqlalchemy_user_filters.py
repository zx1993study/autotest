from sqlalchemy import func, literal

from app.models.resource_record import ResourceRecord


def user_keyword_filter(keyword: str):
    record = ResourceRecord
    data = record.data_json["data"]
    username = func.coalesce(data["username"].as_string(), "")
    real_name = func.coalesce(func.nullif(data["real_name"].as_string(), ""), record.name, "")
    phone = func.coalesce(data["phone"].as_string(), "")
    haystack = func.lower(username + literal(" ") + real_name + literal(" ") + phone)
    return haystack.contains(keyword.strip().lower(), autoescape=True)
