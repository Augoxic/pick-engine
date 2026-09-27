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
