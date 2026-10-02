from hs_uarena_decktracker.card_db import CardData, CardDatabase, cache_is_stale


def test_card_data_preserves_full_card_metadata():
    card = CardData.from_json(
        {
            "id": "BAR_721t",
            "dbfId": 123,
            "name": "Olgra, Mankrik's Wife",
            "text": "Casts When Drawn: Summon Mankrik, who immediately attacks the enemy hero.",
            "type": "SPELL",
            "cardClass": "NEUTRAL",
            "set": "BARRENS",
            "collectible": False,
            "cost": 3,
            "mechanics": ["CASTS_WHEN_DRAWN"],
            "entourage": ["BAR_721"],
            "customFutureField": {"keep": True},
        }
    )

    assert card.card_id == "BAR_721t"
    assert card.type == "SPELL"
    assert card.mechanics == ("CASTS_WHEN_DRAWN",)
    assert card.collectible is False
    assert card.raw["customFutureField"] == {"keep": True}


def test_card_database_loads_all_cards_from_cache(tmp_path):
    cache = tmp_path / "cards.json"
    cache.write_text(
        '{"build":"123456","fetched_at":1,"cards":['
        '{"id":"BAR_721","name":"Mankrik","type":"MINION","text":"Battlecry"},'
        '{"id":"BAR_721t","name":"Olgra","type":"SPELL","collectible":false}'
        ']}',
        encoding="utf-8",
    )

    database = CardDatabase(cache)
    assert database.load() == 2
    assert database.build == "123456"
    assert database.get("BAR_721").name == "Mankrik"
    assert database.get("BAR_721t").collectible is False


def test_missing_card_is_safe(tmp_path):
    cache = tmp_path / "cards.json"
    cache.write_text('{"cards":[]}', encoding="utf-8")
    database = CardDatabase(cache)

    assert database.get("DOES_NOT_EXIST") is None


def test_missing_cache_is_stale(tmp_path):
    assert cache_is_stale(tmp_path / "missing.json")
