from app.shared.utils.slugify import slugify


def test_slugify_basic() -> None:
    assert slugify("My Cool App") == "my-cool-app"


def test_slugify_empty_when_no_latin() -> None:
    assert slugify("!!!") == ""
    assert slugify("Мой проект") == ""
