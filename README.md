# Hearthstone Underground Arena Deck Tracker

A lightweight Linux tracker for **Hearthstone Underground Arena**.

The project is deliberately focused on Underground Arena rather than the other Arena mode.

## Current scope

The first implementation focuses on the client logs that expose Underground Arena state:

- `Arena.log` for draft/deck/redraft events.
- `Power.log` for confirming `GT_UNDERGROUND_ARENA` game sessions.
- Arena draft identity and hero.
- Current 30-card deck snapshots.
- Five-card redraft selections.
- Inferred redraft discards, with completeness information.
- Detection of the transition between `REDRAFTING` and `ACTIVE_DRAFT_DECK`.
- A small Python API that can be used by a future Qt overlay.

The parser infers discarded cards by comparing the settled deck snapshot before a redraft with the settled deck snapshot after it. When the logs do not provide enough evidence, the result is marked incomplete rather than treating the inference as complete.

## Development

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Run the parser against a session directory:

```bash
python -m hs_uarena_decktracker.cli /path/to/Hearthstone_YYYY_MM_DD_HH_MM_SS
```

The parser accepts a Hearthstone log session directory and reads `Arena.log` and `Power.log`.

## Design notes

Underground Arena is identified from `Power.log` by `GT_UNDERGROUND_ARENA`. This is intentional: the tracker should ignore the other Arena mode.

The game currently logs redrafts as:

```text
SetDraftMode - REDRAFTING
Client chooses: ...
Client chooses: ...
Client chooses: ...
Client chooses: ...
Client chooses: ...
SetDraftMode - ACTIVE_DRAFT_DECK
```

The complete deck is logged by `DraftManager.OnChoicesAndContents`.

The CLI JSON output includes both `selected` and `discarded` cards for each redraft, plus `discarded_complete`.

No telemetry or external service is required by the core parser.
