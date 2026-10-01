import json
import sys

from hs_uarena_decktracker import cli


def test_cli_includes_redraft_discard_information(tmp_path, monkeypatch, capsys):
    session = tmp_path / "Hearthstone_2026_10_01_12_00_00"
    session.mkdir()
    (session / "Arena.log").write_text(
        """\
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card A
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 12:01:00.0000000 SetDraftMode - REDRAFTING
D 12:01:01.0000000 Client chooses: X (X)
D 12:01:02.0000000 Client chooses: Y (Y)
D 12:01:03.0000000 Client chooses: Z (Z)
D 12:01:04.0000000 Client chooses: Q (Q)
D 12:01:05.0000000 Client chooses: W (W)
D 12:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card X
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Y
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Z
""",
        encoding="utf-8",
    )
    (session / "Power.log").write_text("GameType=GT_UNDERGROUND_ARENA\\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["hs-uarena", str(session)])
    cli.main()

    result = json.loads(capsys.readouterr().out)
    redraft = result["redrafts"][0]
    assert redraft["selected"] == [
        {"id": "X", "name": "X"},
        {"id": "Y", "name": "Y"},
        {"id": "Z", "name": "Z"},
        {"id": "Q", "name": "Q"},
        {"id": "W", "name": "W"},
    ]
    assert redraft["discarded"] == [
        {"id": "A", "name": None},
        {"id": "B", "name": None},
        {"id": "C", "name": None},
    ]
    assert redraft["discarded_complete"] is False
