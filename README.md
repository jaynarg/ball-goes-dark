# The Ball Goes Dark

An interactive 48-panel World Cup ball. Every nation in the 2026 tournament gets one
panel; the panel dims when the country goes home. Drag to rotate, tap a panel for that
country's results, scorers, and history.

Live: _(add your Vercel URL here)_

## What's in here

| File | Why |
| --- | --- |
| `index.html` | The whole thing. Data, flags, and markup in one file. **This is what deploys.** |
| `template.html` | Same file with `/*__DATA__*/` and `/*__FLAGS__*/` placeholders. Edit this, never `index.html`. |
| `refresh.py` | Pulls live match data, rebuilds `index.html`. Standard library only. |
| `data/flags_b64.json` | 48 flags, rasterized and base64'd once. No need to regenerate. |

## Deploy

No build step. No `npm install`. Nothing runs on Vercel except a static file server.

1. **github.com/new** → name it, Public, **do not** add a README (this one's already here).
2. On the empty repo page: **uploading an existing file** → drag in `index.html`,
   `template.html`, `refresh.py`, `README.md`. Then **Add file → Create new file**, type
   `data/flags_b64.json` in the name box (the slash creates the folder), paste the
   contents, commit.
3. **vercel.com/new** → Import Git Repository → pick the repo.
4. Framework Preset: **Other**. Leave Build Command, Output Directory, and Install
   Command **empty**. Deploy.

Vercel serves `index.html` at the root. Every push to `main` redeploys automatically.

## Refresh the data

Eight matches remain; the final is 19 July. After each one:

```powershell
python refresh.py
```

It fetches the current `worldcup.json`, recomputes everything, and rewrites `index.html`.
Commit that file and Vercel redeploys. The script asserts that goals reconcile
(`named scorers + own goals == goals from scorelines`) both in aggregate and per team,
and refuses to write a file that doesn't balance.

If you'd rather not run anything locally: GitHub's web editor can't run Python, so the
alternative is to paste an updated `index.html` in directly.

## Notes on the data

- **Source:** [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json),
  public domain, no API key. Hand-maintained and updated roughly daily, so it can lag a
  live result by up to a day.
- **Own goals** live in the *beneficiary's* scoreline under the name of an *opposition*
  player. They're excluded from scorer totals and tracked separately, in both directions:
  `og_for` (gifted to you, credited to nobody) and `og_against` (your player, your net).
- **Shootouts** count as draws in the W–D–L record, per statistical convention, with a
  gold arrow marking who advanced. Shootout goals never enter scorer totals, matching
  FIFA's Golden Boot rule.
- **FIFA ranking** is the official 11 June 2026 release — the last one before kickoff,
  published hours before the opening match. It is deliberately *not* updated during the
  tournament. The point of the graphic is the gap between the ranking and what happened.
- **Golden Boot ties** are shown level. FIFA breaks them on assists, then minutes played;
  neither is in this dataset.
- **Flags** are from [lipis/flag-icons](https://github.com/lipis/flag-icons), rasterized
  to 160×120 and quantized to 96 colors. England and Scotland use the `gb-eng` / `gb-sct`
  subdivision codes, since neither is a country in ISO 3166.

## Known dependency

The page loads three.js from cdnjs and fonts from Google. Fonts degrade gracefully; three.js
does not. If you need a genuinely offline file, inline `three.min.js` into `template.html`
(adds ~600 KB) and drop the `<script src>` tag.
