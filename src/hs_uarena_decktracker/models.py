from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Card:
    card_id: str
    name: str | None = None

    def display_name(self) -> str:
        return self.name or self.card_id


@dataclass(frozen=True)
class DeckSnapshot:
    timestamp: str
    deck_id: str
    cards: tuple[Card, ...]

    @property
    def card_ids(self) -> frozenset[str]:
        return frozenset(card.card_id for card in self.cards)


@dataclass(frozen=True)
class Redraft:
    number: int
    started_at: str
    selected: tuple[Card, ...]
    ended_at: str | None = None


@dataclass
class ArenaRun:
    deck_id: str | None = None
    hero_card_id: str | None = None
    underground: bool = False
    deck_snapshots: list[DeckSnapshot] = field(default_factory=list)
    redrafts: list[Redraft] = field(default_factory=list)

    @property
    def current_deck(self) -> DeckSnapshot | None:
        return self.deck_snapshots[-1] if self.deck_snapshots else None
