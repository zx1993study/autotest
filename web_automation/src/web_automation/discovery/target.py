"""Identity checks for the configured discovery page, including hash routes."""
import re
from urllib.parse import parse_qsl, urlsplit


def is_login_url(url: str) -> bool:
    location = urlsplit(url)
    routes = [location.path, urlsplit(location.fragment.lstrip("!")).path]
    return any(re.search(r"(?:^|/)(?:login|signin|sign-in)(?:/|$)", route, re.IGNORECASE) for route in routes)


def _route(location):
    fragment = location.fragment.lstrip("!")
    hashed = urlsplit(fragment) if fragment.startswith("/") else None
    return (
        (location.path or "/").rstrip("/") or "/",
        (hashed.path.rstrip("/") or "/") if hashed else "",
        parse_qsl(location.query, keep_blank_values=True),
        parse_qsl(hashed.query, keep_blank_values=True) if hashed else [],
    )


def matches_target_page(target_url: str, actual_url: str) -> bool:
    try:
        target, actual = urlsplit(target_url), urlsplit(actual_url)
        target_origin = (target.scheme.lower(), target.hostname, target.port or (443 if target.scheme == "https" else 80))
        actual_origin = (actual.scheme.lower(), actual.hostname, actual.port or (443 if actual.scheme == "https" else 80))
        if not target.hostname or target_origin != actual_origin:
            return False
        expected, observed = _route(target), _route(actual)
        return expected[:2] == observed[:2] and all(
            all(observed[index].count(pair) >= expected[index].count(pair) for pair in expected[index])
            for index in (2, 3)
        )
    except ValueError:
        return False


def require_target_page(target_url: str, actual_url: str) -> None:
    if not matches_target_page(target_url, actual_url):
        raise RuntimeError("浏览器已跳转到其他页面，已停止分析；请检查目标页面地址与登录状态")
