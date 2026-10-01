from hs_uarena_decktracker.arena_log import ArenaLogParser


def test_parses_underground_redraft(tmp_path):
    arena_log = tmp_path / "Arena.log"
    arena_log.write_text(
        """D 13:23:42.9727764 DraftManager.OnChoicesAndContents - Draft Deck ID: 3379498479, Hero Card = HERO_11
D 13:23:42.9727764 DraftManager.OnChoicesAndContents - Draft deck contains card TIME_612
D 13:23:42.9727764 DraftManager.OnChoicesAndContents - Draft deck contains card FIR_900
D 13:23:42.9727764 SetDraftMode - REDRAFTING
D 13:24:02.7890685 Client chooses: Blood Draw (TIME_612)
D 13:24:06.9731301 Client chooses: Fae Trickster (EDR_571)
D 13:24:09.3091646 Client chooses: Cremate (FIR_900)
D 13:24:26.0594095 Client chooses: Drink Blood (JAIL_441)
D 13:24:33.6905201 Client chooses: Frostbitten Imp (CATA_612)
D 13:24:34.0035246 SetDraftMode - ACTIVE_DRAFT_DECK
""",
        encoding="utf-8",
    )

    run = ArenaLogParser().parse(arena_log)

    assert run.deck_id == "3379498479"
    assert run.hero_card_id == "HERO_11"
    assert [c.card_id for c in run.current_deck.cards] == ["TIME_612", "FIR_900"]
    assert len(run.redrafts) == 1
    assert [c.card_id for c in run.redrafts[0].selected] == [
        "TIME_612", "EDR_571", "FIR_900", "JAIL_441", "CATA_612"
    ]
    assert run.redrafts[0].ended_at == "13:24:34.0035246"


def test_does_not_require_exactly_thirty_cards(tmp_path):
    arena_log = tmp_path / "Arena.log"
    arena_log.write_text(
        "D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_1\n"
        "D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card ABC_1\n",
        encoding="utf-8",
    )
    run = ArenaLogParser().parse(arena_log)
    assert len(run.current_deck.cards) == 1
