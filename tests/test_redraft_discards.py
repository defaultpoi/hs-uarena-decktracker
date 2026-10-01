from hs_uarena_decktracker.arena_log import ArenaLogParser


def test_infers_all_five_discards_from_snapshot_diff(tmp_path):
    arena_log = """\
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card A
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card D
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card E
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card F
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card G
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card H
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card I
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card J
D 12:01:00.0000000 SetDraftMode - REDRAFTING
D 12:01:01.0000000 Client chooses: X (X)
D 12:01:02.0000000 Client chooses: Y (Y)
D 12:01:03.0000000 Client chooses: Z (Z)
D 12:01:04.0000000 Client chooses: Q (Q)
D 12:01:05.0000000 Client chooses: W (W)
D 12:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card F
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card G
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card H
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card I
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card J
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card X
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Y
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Z
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Q
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card W
"""
    (tmp_path / "Arena.log").write_text(arena_log, encoding="utf-8")

    run = ArenaLogParser().parse(tmp_path / "Arena.log")
    redraft = run.redrafts[0]

    assert [card.card_id for card in redraft.discarded] == ["A", "B", "C", "D", "E"]
    assert redraft.discarded_complete is True


def test_keeps_partial_discard_evidence_when_snapshot_is_incomplete(tmp_path):
    arena_log = """\
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card A
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card D
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card E
D 12:01:00.0000000 SetDraftMode - REDRAFTING
D 12:01:01.0000000 Client chooses: X (X)
D 12:01:02.0000000 Client chooses: Y (Y)
D 12:01:03.0000000 Client chooses: Z (Z)
D 12:01:04.0000000 Client chooses: Q (Q)
D 12:01:05.0000000 Client chooses: W (W)
D 12:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card D
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card E
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card X
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Y
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Z
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card Q
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card W
"""
    (tmp_path / "Arena.log").write_text(arena_log, encoding="utf-8")

    redraft = ArenaLogParser().parse(tmp_path / "Arena.log").redrafts[0]

    assert [card.card_id for card in redraft.discarded] == ["A"]
    assert redraft.discarded_complete is False
