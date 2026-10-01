from hs_uarena_decktracker.arena_log import ArenaLogParser


def test_tracks_discards_per_redraft(tmp_path):
    lines = [
        "D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11",
    ]
    lines += [
        f"D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card {card}"
        for card in "ABCDEFGHIJ"
    ]
    lines += [
        "D 12:01:00.0000000 SetDraftMode - REDRAFTING",
        "D 12:01:00.5000000 DraftManager.OnRedraftBegin - Got new redraft deck with ID: 100",
        "D 12:01:01.0000000 Client chooses: X (X)",
        "D 12:01:02.0000000 Client chooses: Y (Y)",
        "D 12:01:03.0000000 Client chooses: Z (Z)",
        "D 12:01:04.0000000 Client chooses: Q (Q)",
        "D 12:01:05.0000000 Client chooses: W (W)",
        "D 12:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK",
        "D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11",
    ]
    lines += [
        f"D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card {card}"
        for card in "CFGHIXYZQW"
    ]
    # A later snapshot can reflect ordinary gameplay mutations. It must
    # not become the endpoint used to infer the earlier redraft.
    lines += [
        f"D 12:02:30.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11",
    ]
    lines += [
        f"D 12:02:30.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card {card}"
        for card in "CFGHIXYZQ"
    ]
    lines += [
        "D 12:03:00.0000000 SetDraftMode - REDRAFTING",
        "D 12:03:01.0000000 Client chooses: B (B)",
        "D 12:03:02.0000000 Client chooses: C (C)",
        "D 12:03:03.0000000 Client chooses: R (R)",
        "D 12:03:04.0000000 Client chooses: S (S)",
        "D 12:03:05.0000000 Client chooses: T (T)",
        "D 12:03:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK",
        "D 12:04:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11",
    ]
    # Simulate a later redraft state: only C is demonstrably removed.
    lines += [
        f"D 12:04:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card {card}"
        for card in "FGHIXYZQW"
    ]
    lines += [
        "D 12:04:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card R",
    ]

    (tmp_path / "Arena.log").write_text("\n".join(lines), encoding="utf-8")
    run = ArenaLogParser().parse(tmp_path / "Arena.log")

    assert len(run.redrafts) == 2
    assert run.redrafts[0].redraft_deck_id == "100"
    assert run.redrafts[1].redraft_deck_id is None
    assert [card.card_id for card in run.redrafts[0].discarded] == ["A", "B", "D", "E", "J"]
    assert run.redrafts[0].discarded_complete is True
    assert [card.card_id for card in run.redrafts[1].discarded] == ["C"]
    assert run.redrafts[1].discarded_complete is False
