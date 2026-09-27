# The site

## Structure
One HTML file. Sticky dark tab bar at the top: built sports are live tabs, planned ones are disabled "soon" tabs.
Each tab has a hash (#nfl, #epl) and arrow-key navigation. Each sport panel has: title, explainer, a hero graphic,
the backtest table with an honest warning, the "How each Claude model nudged the math" table, filters, then games
grouped by kickoff time in ET.

## Visuals
- NFL: the field strip. Margin from away end zone (left) to home end zone (right), line every 5 points.
  Marks: Elo (ring), Elo + efficiency (dot), Combined (diamond), Claude (purple squares), Vegas (orange bar).
- EPL: the pitch bar split into home / draw / away by probability, orange ticks where the market splits it.
- Palette: turf greens, chalk white, pylon orange for the market, purple for Claude, navy for models.
  Fonts: Barlow Condensed (display) and Barlow (body). Light and dark themes via CSS tokens.

## Filters
NFL: all, winner in doubt (any predictor picks the other side), model vs Vegas winner, 3+ points off the line.
EPL: all, result in doubt (favourite outcome differs across predictors), model vs market favourite, 8+ points off
the market on any outcome.

## Viewer gotchas (both caused real bugs)
1. The claude.ai viewer defines a global `claude`. A top-level `let claude` threw "Identifier 'claude' has already
   been declared" and the whole script never ran: blank dark page. Fix: everything inside one IIFE, no global named
   `claude`.
2. The viewer runs pages in a sandboxed frame, where `history.replaceState` throws. Wrap URL/history calls in
   try/catch.
Also: build each sport inside try/catch so one broken tab shows a message instead of blanking the site, and show a
"Loading…" line plus a window error handler that prints errors on the page.

## Testing before publishing
Playwright: load the page inside `<iframe sandbox="allow-scripts" srcdoc=...>` and again with an injected
`<script>const claude = {use: async () => null};</script>` in the head. Expect all tabs, all games, no page errors.
Check a 390px-wide mobile view too.

## Injury report (NFL cards)
Each game card lists starters and key players who are Out or Doubtful (red) or Questionable (grey), and a red note
when a listed starting QB is ruled out ("Jayden Daniels is Out; Marcus Mariota expected to start"). Built by
`injuries.py` from nflverse injury reports plus the latest depth chart. The model panel warns when a slate's nudges
were made with a prompt older than v6, since those models did not see the injury report.

## My Bets tab
Private bet log per signed-in viewer, stored with the artifact `db` capability:
- Bets: collection `data/users/<viewer id>`, one document per bet (`bet_...`), plus a `settings` document.
- Leaderboard: collection `leaderboard`, one summary document per viewer who opts in (totals only, never bets).
- Declared capabilities: `db` with rules `{path: "leaderboard", read: "view", write: "admin"}` and
  `{path: "leaderboard/{self}", write: "interact"}`, plus `user` with scopes `["profile"]` for names.
- Linking a bet to a sheet game fills in the model's chance (moneyline, spread, EPL result, anytime TD) and lets the
  page suggest the result from the final score. Open bets are sorted by kickoff with a "starts in" countdown.
- Import: paste CSV lines `date, sport, bet, type, odds, stake, result`.
- Pages that declare `db` cannot be shared by public link; friends need to be in the owner's Claude organization and
  have Contributor access to save bets or join the leaderboard.
- FanDuel has no public API for account history, so nothing syncs automatically.
