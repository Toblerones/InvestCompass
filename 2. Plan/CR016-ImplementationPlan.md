# CR016 Implementation Plan: Prompt Cleanup — Narrative Sanitisation, Max Positions Bug, Decision Question Deduplication

**Created**: March 27, 2026
**Status**: Ready for implementation
**CR Reference**: `3. ChangeLog/CR016 - Prompt Cleanup — Narrative Sanitisation, Max Positions Bug, Decision Question Deduplication.md`
**Depends on**: CR014 (sanitise_narrative_update), CR015 (stop-loss rule removal)

---

## Summary

Three small issues found after CR014/CR015:

1. **Bug** — `config.json` `max_positions` is 5, should be 3. Confirmed: current value is 5.
2. **Data** — MSFT `stop_loss_exit` narrative contains execution state ("Position exited") and a cost basis price ("$434.00 entry"), violating CR011 narrative boundary rule. Also references the old -10% hard stop removed in CR015.
3. **Prompt** — `strategy.txt` HOLD/EXIT decision block duplicates the thesis assessment that now precedes it. Two of its four questions are already answered by the THESIS ASSESSMENT block.

---

## Files Modified

| File | Change |
|------|--------|
| [App/config/config.json](../App/config/config.json) | `max_positions`: 5 → 3 |
| [App/config/narratives.json](../App/config/narratives.json) | Clean MSFT `stop_loss_exit` summary — remove execution state and cost basis |
| [App/config/strategy.txt](../App/config/strategy.txt) | Reduce HOLD/EXIT block to single opportunity-cost question |

`narrative_manager.py` — no change needed. `sanitise_narrative_update()` is already called at the top of `update_narratives()` (CR014). This is a one-time data fix to the existing stale content.

---

## Change 1: `config.json`

```json
"max_positions": 3
```

---

## Change 2: `narratives.json` — MSFT `stop_loss_exit` summary

**Current** (violates boundary rule):
```
Updated: Hard stop-loss triggered at -10.4% from $434.00 entry. Position exited.
Thesis remained intact at exit — exit was macro and sector-driven...
```

**Replace with** (market intelligence only):
```
MSFT previously exited after a significant drawdown driven by macro and sector
weakness. Thesis was intact at exit — no fundamental deterioration observed.
Monitor for re-entry when the Amazon-OpenAI Azure dispute (active narrative) resolves
or when macro conditions stabilise.
```

---

## Change 3: `strategy.txt` — HOLD/EXIT decision block

**Current** (4 questions, first two duplicate thesis assessment):
```
HOLD / EXIT decision:
- Why is it falling — macro or stock-specific?
- Is the thesis intact, weakening, or broken? (count negative signals)
- Is the stop-loss breached? (check SITUATION SUMMARY)
- Is there a better use of this capital?
```

**Replace with** (1 question — the only additive one):
```
HOLD / EXIT decision (after thesis assessment):
- Is there a better use of this capital right now?
```

The thesis assessment block already covers: macro vs stock-specific, thesis integrity, and negative signal count. The stop-loss check is in the SITUATION SUMMARY. Only the opportunity-cost question is additive.

---

## Verification

1. `python -c "import json; c=json.load(open('App/config/config.json')); print(c['max_positions'])"` → `3`
2. Run `--manual`, open prompt file — Situation Summary shows `1 position(s), 2 slot(s) available` and Constraints shows `Maximum positions: 3`
3. Check `narratives.json` MSFT `stop_loss_exit` summary — no cost basis dollars, no "Position exited", no "-10%" reference
4. `strategy.txt` HOLD/EXIT block is one line
