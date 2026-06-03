import re

_DEFAULT_MAX_LENGTH = 64


def slugify(value: str, *, max_length: int = _DEFAULT_MAX_LENGTH) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:max_length]
