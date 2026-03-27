# CR016: Prompt Cleanup — Narrative Sanitisation, Max Positions Bug, Decision Question Deduplication

**Version**: 1.0
**Date**: March 27, 2026
**Author**: Tobes (Product Owner)
**Type**: Cleanup / Bug fix
**Scope**: `config.json`, `narratives.json`, `narrative_manager.py`, `strategy.txt`
**Depends on**: CR014 (sanitise_narrative_update), CR015 (stop-loss rule removal)

---

## 1. Three Issues

---

### Issue 1 (Bug): Max positions inconsistency

**Observed**: Situation Summary displays "4 slot(s) available" (implying max 5).
Constraints block displays "Maximum positions: 5".
PRD and original config both specify max 3.

**Root cause**: `config.json` `max_positions` value has drifted to 5, or the display
logic is reading the wrong field.

**Fix**: Audit `config.json` and confirm `max_positions` is set to 3. Audit all
references to `max_positions` in `ai_agent.py` and `display.py` to ensure they
read from a single source.

```json
"max_positions": 3
```

After fix, Situation Summary should read:
```
Portfolio: 1 position(s), 2 slot(s) available.
```

---

### Issue 2 (Data): Stale narrative in MSFT — Stop Loss Exit theme

**Observed**: The MSFT `Stop Loss Exit` narrative contains:
> *"Hard stop-loss triggered at -10.4% from $434.00 entry. Position exited."*

This violates the narrative boundary rule (CR011) on two counts:
- Contains portfolio execution state ("position exited")
- References a cost basis price level ("$434.00 entry")

It also references the old -10% hard stop-loss rule which no longer exists after CR015.

**Fix — `narratives.json`**: Manually clean the MSFT Stop Loss Exit theme summary.
Replace with market-intelligence-only version:

```
MSFT exited previously after a significant drawdown. Thesis was intact at exit —
weakness was macro and sector-driven, not fundamental. Monitor for re-entry
when Priority 2 catalyst (Amazon-OpenAI AWS dispute) resolves.
```

**Fix — `narrative_manager.py`**: Confirm `sanitise_narrative_update()` (introduced
in CR014) is called on every narrative write. This prevents recurrence — any future
update containing cost basis, share counts, or execution language will be stripped
before write.

---

### Issue 3 (Prompt): HOLD/EXIT decision questions duplicate thesis assessment

**Observed**: The DECISION QUESTIONS block contains two sections that ask the same
question in different words:

```
THESIS ASSESSMENT:
  Is this weakness primarily macro-driven or reflects genuine thesis deterioration?

HOLD / EXIT decision:
  - Why is it falling — macro or stock-specific?
  - Is the thesis intact, weakening, or broken?
  ...
```

The first two HOLD/EXIT questions are fully covered by the thesis assessment above.
This adds prompt length and risks the LLM treating them as separate checks.

**Fix — `strategy.txt`**: Reduce HOLD/EXIT decision questions to the one question
not covered by thesis assessment:

```
HOLD / EXIT decision (after thesis assessment):
- Is there a better use of this capital right now?
```

The thesis assessment already covers: why it's falling, thesis integrity, and
macro vs stock-specific distinction. The only additive question is opportunity cost.

---

## 2. Files Changed

| File | Change | Description |
|------|--------|-------------|
| `config.json` | Bug fix | Confirm `max_positions: 3` |
| `narratives.json` | Data fix | Clean MSFT Stop Loss Exit theme — remove execution state and cost basis reference |
| `narrative_manager.py` | Confirm | Verify `sanitise_narrative_update()` is called on every write (CR014 dependency) |
| `strategy.txt` | Simplification | Reduce HOLD/EXIT block to single opportunity-cost question |

---

## 3. Files NOT Changed

Everything else. This is cleanup only.

---

## 4. Success Criteria

- [ ] Situation Summary shows "2 slot(s) available" (not 4)
- [ ] Constraints block shows "Maximum positions: 3" (not 5)
- [ ] MSFT narrative contains no cost basis, share counts, or execution language
- [ ] `sanitise_narrative_update()` called on every narrative write
- [ ] HOLD/EXIT decision block is one line in strategy.txt
- [ ] Total prompt line count reduced by ~6 lines vs post-CR014/CR015

---

**Product Owner**: Tobes
**Date**: March 27, 2026
**Status**: Draft — ready for Claude Code handoff