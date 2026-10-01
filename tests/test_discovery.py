from hs_uarena_decktracker.discovery import latest_session


def test_latest_session(tmp_path):
    first = tmp_path / "Hearthstone_1"
    second = tmp_path / "Hearthstone_2"
    first.mkdir()
    second.mkdir()

    first.touch()
    second.touch()

    # The function should return a session directory when present.
    assert latest_session(tmp_path) in {first, second}
