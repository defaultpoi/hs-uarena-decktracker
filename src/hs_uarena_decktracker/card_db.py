from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_URL = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json"
DEFAULT_CACHE = Path("~/.cache/hs-uarena-decktracker/cards.enUS.json").expanduser()
DEFAULT_MAX_AGE = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class CardData:
    """Complete normalized card metadata with the original JSON preserved."""

    card_id: str
    dbf_id: int | None = None
    name: str | None = None
    text: str | None = None
    collection_text: str | None = None
    flavor: str | None = None
    type: str | None = None
    card_class: str | None = None
    set: str | None = None
    rarity: str | None = None
    faction: str | None = None
    races: tuple[str, ...] = ()
    spell_school: str | None = None
    multi_class_group: str | None = None
    classes: tuple[str, ...] = ()
    mechanics: tuple[str, ...] = ()
    referenced_tags: tuple[str, ...] = ()
    play_requirements: dict[str, Any] | None = None
    entourage: tuple[str, ...] = ()
    collectible: bool | None = None
    elite: bool | None = None
    cost: int | None = None
    attack: int | None = None
    health: int | None = None
    durability: int | None = None
    armor: int | None = None
    overload: int | None = None
    spell_damage: int | None = None
    hide_stats: bool | None = None
    targeting_arrow_text: str | None = None
    how_to_earn: str | None = None
    how_to_earn_golden: str | None = None
    artist: str | None = None
    raw: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "CardData":
        return cls(
            card_id=value["id"],
            dbf_id=value.get("dbfId"),
            name=value.get("name"),
            text=value.get("text"),
            collection_text=value.get("collectionText"),
            flavor=value.get("flavor"),
            type=value.get("type"),
            card_class=value.get("cardClass"),
            set=value.get("set"),
            rarity=value.get("rarity"),
            faction=value.get("faction"),
            races=tuple(value.get("races", value.get("race", [])) or []),
            spell_school=value.get("spellSchool"),
            multi_class_group=value.get("multiClassGroup"),
            classes=tuple(value.get("classes", []) or []),
            mechanics=tuple(value.get("mechanics", []) or []),
            referenced_tags=tuple(value.get("referencedTags", []) or []),
            play_requirements=value.get("playRequirements"),
            entourage=tuple(value.get("entourage", []) or []),
            collectible=value.get("collectible"),
            elite=value.get("elite"),
            cost=value.get("cost"),
            attack=value.get("attack"),
            health=value.get("health"),
            durability=value.get("durability"),
            armor=value.get("armor"),
            overload=value.get("overload"),
            spell_damage=value.get("spellDamage"),
            hide_stats=value.get("hideStats"),
            targeting_arrow_text=value.get("targetingArrowText"),
            how_to_earn=value.get("howToEarn"),
            how_to_earn_golden=value.get("howToEarnGolden"),
            artist=value.get("artist"),
            raw=dict(value),
        )


class CardDatabase:
    """Cached HearthstoneJSON card database.

    The cache contains every card, including generated/non-collectible cards.
    Updating is explicit so the tracker never performs network I/O on its
    one-second GUI refresh path.
    """

    def __init__(
        self,
        cache_path: str | Path = DEFAULT_CACHE,
        source_url: str = DEFAULT_URL,
    ) -> None:
        self.cache_path = Path(cache_path).expanduser()
        self.source_url = source_url
        self._cards: dict[str, CardData] | None = None
        self.build: str | None = None
        self.fetched_at: float | None = None

    def load(self) -> int:
        payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        cards = payload.get("cards", payload)
        if not isinstance(cards, list):
            raise ValueError("invalid HearthstoneJSON cache: cards is not a list")
        self._cards = {
            card["id"]: CardData.from_json(card)
            for card in cards
            if isinstance(card, dict) and card.get("id")
        }
        self.build = payload.get("build") if isinstance(payload, dict) else None
        self.fetched_at = payload.get("fetched_at") if isinstance(payload, dict) else None
        return len(self._cards)

    def update(self, timeout: float = 30.0) -> int:
        request = Request(
            self.source_url,
            headers={"User-Agent": "hs-uarena-decktracker/0.1"},
        )
        with urlopen(request, timeout=timeout) as response:
            cards = json.load(response)
            final_url = response.geturl()

        if not isinstance(cards, list):
            raise ValueError("HearthstoneJSON response is not a card list")

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_url": final_url,
            "fetched_at": time.time(),
            "build": self._build_from_url(final_url),
            "cards": cards,
        }
        self.cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        return self.load()

    def ensure_loaded(self) -> int:
        if self._cards is None:
            return self.load()
        return len(self._cards)

    def get(self, card_id: str) -> CardData | None:
        self.ensure_loaded()
        return self._cards.get(card_id) if self._cards is not None else None

    def find_by_name(self, name: str) -> tuple[CardData, ...]:
        """Return cards whose database name exactly matches the supplied name."""
        self.ensure_loaded()
        if self._cards is None:
            return ()
        return tuple(card for card in self._cards.values() if card.name == name)

    def __len__(self) -> int:
        self.ensure_loaded()
        return len(self._cards or {})

    @staticmethod
    def _build_from_url(url: str) -> str | None:
        match = re.search(r"/v1/(\\d+)/", url)
        return match.group(1) if match else None


def cache_is_stale(
    cache_path: str | Path = DEFAULT_CACHE,
    max_age: float = DEFAULT_MAX_AGE,
) -> bool:
    path = Path(cache_path).expanduser()
    try:
        age = time.time() - path.stat().st_mtime
    except FileNotFoundError:
        return True
    return age >= max_age
