"""
Parses GitHub's RFC 5988 `Link` header into a simple dict, e.g.:
  {"next": "https://api.github.com/...&page=2", "last": "..."}
"""
import re

_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


def parse_link_header(link_header: str | None) -> dict[str, str]:
    if not link_header:
        return {}
    return {rel: url for url, rel in _LINK_RE.findall(link_header)}
