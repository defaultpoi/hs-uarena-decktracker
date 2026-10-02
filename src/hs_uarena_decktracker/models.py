from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Card:
    card_id: str
    name: str | None = None
    text: str | None = None

    def display_name(self) -> str:
        return self.name or self.card_id

    def display_text(self) -> str:
        return self.text or ""


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
    redraft_deck_id: str | None = None
    ended_at: str | None = None
    discarded: tuple[Card, ...] = ()
    discarded_complete: bool = False


@dataclass(frozen=True)
class GeneratedDeckCard:
    """A card created by another card and observed entering the local deck."""

    card: Card
    source_card: Card
    trigger: str
    event: str
    reason: str
    entity_id: int | None = None
    source_entity_id: int | None = None
    game_index: int | None = None
    in_deck: bool = True
    final_zone: str | None = None

    @property
    def generated(self) -> Card:
        return self.card

    @property
    def source(self) -> Card:
        return self.source_card


DeckEffect = GeneratedDeckCard


@dataclass
class ArenaRun:
    deck_id: str | None = None
    hero_card_id: str | None = None
    underground: bool = False
    losses: int = 0
    last_result: str | None = None
    game_results: list[str] = field(default_factory=list)
    deck_snapshots: list[DeckSnapshot] = field(default_factory=list)
    redrafts: list[Redraft] = field(default_factory=list)
    start_of_game_duplicates: list[Card] = field(default_factory=list)
    generated_deck_cards: list[Card] = field(default_factory=list)
    deck_effects: list[GeneratedDeckCard] = field(default_factory=list)

    @property
    def run_ended(self) -> bool:
        return self.losses >= 3

    @property
    def current_deck(self) -> DeckSnapshot | None:
        if not self.deck_snapshots:
            return None
        return self.deck_snapshots[-1]

    @property
    def effective_deck(self) -> tuple[Card, ...]:
        """Best known deck state from the latest draft plus current generated cards."""
        snapshot = self.current_deck
        if snapshot is None:
            return ()

        cards = list(snapshot.cards)
        cards.extend(effect.card for effect in self.deck_effects if effect.in_deck)
        return tuple(cards)

    @property
    def effective_deck_counts(self) -> Counter[str]:
        return Counter(card.card_id for card in self.effective_deck)
