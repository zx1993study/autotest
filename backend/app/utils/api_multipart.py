from app.schemas.api_request_file import MAX_API_FILE_SIZE, ApiRequestFile
from app.services.api_request_file_service import ApiRequestFileService
from pydantic import TypeAdapter
from urllib3.filepost import encode_multipart_formdata


def request_files(value) -> list[dict]:
    references = TypeAdapter(list[ApiRequestFile]).validate_python(value)
    if len(references) > 4 or sum(item.size for item in references) > MAX_API_FILE_SIZE:
        raise ValueError("API 请求最多 4 个文件，合计不超过 10MB")
    return [item.model_dump() for item in references]


def multipart_bytes(repository, request: dict, headers: dict) -> bytes:
    if request["method"] in {"GET", "HEAD"}:
        raise ValueError("GET/HEAD 请求不支持文件上传")
    body = request.get("body") or {}
    if not isinstance(body, dict):
        raise ValueError("文件上传的表单参数必须为对象")
    fields = []
    for name, value in body.items():
        if isinstance(value, (dict, list)):
            raise ValueError("文件上传表单字段仅支持标量值")
        if value is not None:
            fields.append((str(name), str(value).lower() if isinstance(value, bool) else str(value)))
    service = ApiRequestFileService(repository)
    for raw in request_files(request.get("files", [])):
        reference = ApiRequestFile.model_validate(raw)
        content = service.read(int(request["project_id"]), reference)
        fields.append((reference.field, (reference.filename, content, reference.content_type)))
    encoded, content_type = encode_multipart_formdata(fields)
    for key in list(headers):
        if key.lower() in {"content-type", "content-length", "transfer-encoding"}:
            del headers[key]
    headers["Content-Type"] = content_type
    return encoded
