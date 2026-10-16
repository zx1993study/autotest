from app.core.exceptions import BusinessRuleError


def normalize_auth_token(value: str, auth_type: str = "bearer") -> str:
    token = value.strip()
    if not token:
        return ""
    if len(token) > 16384:
        raise BusinessRuleError("Token 长度不能超过 16384 个字符")
    if any(ord(char) < 32 or ord(char) == 127 for char in token):
        raise BusinessRuleError("请仅输入一个 Token，不要包含换行或控制字符")
    if auth_type.lower() == "bearer":
        parts = token.split(maxsplit=1)
        if parts[0].lower() == "bearer":
            token = parts[1].strip() if len(parts) == 2 else ""
        if not token or any(char.isspace() for char in token):
            raise BusinessRuleError("请输入有效的 Token 或 Bearer Token")
    return token
