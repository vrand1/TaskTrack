import re

_TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: set[str] = set()
    for raw in tags:
        tag = raw.strip().lower()
        if not tag:
            continue
        if not _TAG_PATTERN.fullmatch(tag):
            raise ValueError(
                f"Некорректный тег '{raw}': используйте 1-64 символа, "
                "строчные буквы, цифры, '_' или '-'"
            )
        normalized.add(tag)
    return sorted(normalized)
