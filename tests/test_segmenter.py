from app.segmenter import restore_text


def test_restore_spaces() -> None:
    restored = restore_text("куплюайфон14про")

    assert "куплю" in restored
    assert "айфон" in restored
    assert "14" in restored


def test_restore_known_prefix_without_inner_split() -> None:
    restored = restore_text("ищудомвПодмосковье")

    assert restored.startswith("ищу ")
    assert "дом" in restored
