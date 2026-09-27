# Claude nudges

## The four setups (same for every sport)
| Key | Row on the sheet | Model id | Prompt | Request settings |
|---|---|---|---|---|
| haiku_v4 | Haiku 4.5 (prompt v4) | claude-haiku-4-5-20251001 | v4 | temperature 0, no thinking |
| haiku | Haiku 4.5 | claude-haiku-4-5-20251001 | current (NFL v6, EPL v5) | temperature 0, no thinking |
| sonnet | Sonnet 5 | claude-sonnet-5 | current (NFL v6, EPL v5) | adaptive thinking on by default, default effort (high); no temperature |
| opus | Opus 5.5 | claude-opus-5-5 | current (NFL v6, EPL v5) | adaptive thinking always on, default effort (medium); no temperature |

Sonnet 5 rejects non-default temperature/top_p/top_k with a 400. Opus 5.5 cannot disable thinking.
Responses may contain thinking blocks: read only `type == "text"` blocks. Use max_tokens 16000.
Check current model ids and defaults in the Claude Platform docs before changing these.

## Prompts
- v4 (original, looser): describes the model's output, says lines are hidden, asks for an adjustment within the
  range with a reason.
- v5 (current): also lists everything the math already covers, says to nudge only for what the math cannot see,
  that most games should get 0, and that luck and small samples are not reasons. Sport hints: NFL = starting QB
  changes and extreme weather; EPL = do not nudge on early-season form or table position alone.
- v6 (NFL, current): v5 plus the injury report. Facts now carry `injuries` (starters and key players Out,
  Doubtful or Questionable, from nflverse injury reports and depth charts) and `qb_note` when the listed starting QB
  is ruled out (`starting_qb` then names the expected backup). Guidance: Out/Doubtful players miss the game,
  Questionable usually play, and apart from QB one player is rarely worth more than 1 to 2 points.
- Each sport's newest prompt is `current` in `SPORTS` in nudge.py; the saved nudge records the exact version.
- Output contract for all versions: a bare JSON array of `{"id", "nudge", "reason"}`, positive = toward the home side.

## Ranges
NFL: +/-7 points on the combined margin. EPL: +/-1.0 goal on expected goal difference, then the page recomputes
win/draw/loss with the exported logistic coefficients.

## Locking
- One request per setup per slate, containing only games that have not kicked off and have no saved nudge.
- Saved to `nudges/<sport>/<slate>.json` after each setup, so a failure midway loses nothing.
- Never overwrite an existing nudge. Clamp values to the range. Store model, prompt version and UTC timestamp.
- Never include the market, odds or spreads in any payload.

## Why not the in-page button
The claude.ai runtime `sample` capability only chooses a tier (quick/default/complex) and may substitute a
cheaper one, so it cannot guarantee specific models. The API pipeline can.
