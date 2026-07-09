# The Ball Goes Dark

An interactive World Cup ball. Forty-two panels — the number a soccer ball actually has —
each one a nation. The panel dims when the country goes home. Drag to rotate, tap a panel
for that country's results, scorers, and history.

## Why 42 and not 48

A soccer ball is a Goldberg polyhedron, and Goldberg polyhedra have **10T + 2** faces
where T = m² + mn + n². The sequence runs 12, 32, **42**, 72, 92. Forty-eight is not in it,
so a 48-cell sphere can only be an irregular Voronoi mush — cell areas vary by 40%.

Forty-two is GP(2,0), the chamfered dodecahedron: **12 pentagons and 30 hexagons**, cell
areas within 6%. It's built by subdividing an icosahedron once and taking its 42 vertices
(12 originals, 30 edge midpoints) as Voronoi seeds.

The 12 pentagons are the 12 group winners. Six group-stage exits — Uzbekistan, Saudi
Arabia, Qatar, Tunisia, Turkey, Curaçao — have no panel. They're still fully searchable,
and their cards say so. `refresh.py` asserts 42 panels and 12 pentagons and refuses to
build otherwise, so if a group winner ever lands on the no-panel list the build fails loudly.

Live: _(add your Vercel URL here)_

## What's in here

| File | Why |
| --- | --- |
| `index.html` | The whole thing. Data, flags, and markup in one file. **This is what deploys.** |
| `template.html` | Same file with `/*__DATA__*/` and `/*__FLAGS__*/` placeholders. Edit this, never `index.html`. |
| `refresh.py` | Pulls live match data, rebuilds `index.html`. Standard library only. |
| `data/flags_b64.json` | 48 flags, rasterized and base64'd once. Never needs regenerating. |
| `data/teams.json` | Written by `refresh.py`, read by `render_assets.py`. Commit it. |
| `render_assets.py` | Redraws the OG card and icons from the live standings. Needs Pillow. |
| `og.png`, `favicon.*`, `apple-touch-icon.png`, `icon-*.png`, `site.webmanifest` | Social card, favicons, home-screen icon. All served from the root. |

The favicon is a plain truncated-icosahedron football — twelve black pentagons, twenty
white hexagons, one pentagon gold — because the 48-panel ball is unreadable at 16px. The
home-screen and PWA icons sit on a **white** plate; a near-black ball on a near-black
square vanishes against a dark wallpaper.

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
5. In Vercel, set the project name so the domain is **ball-goes-dark.vercel.app** — the
   meta tags and the OG card are already hardcoded to it. If you take a different domain,
   change the four `ball-goes-dark.vercel.app` strings in `template.html` (canonical,
   `og:url`, `og:image`, `twitter:image`), change `SITE` in `render_assets.py`, then rerun
   both scripts. `og:image` must be absolute; iMessage, Slack and X will not resolve a
   relative one.

Vercel serves `index.html` at the root. Every push to `main` redeploys automatically.

### Checking the card

Once redeployed, paste the URL into
[opengraph.xyz](https://www.opengraph.xyz/) or Slack's own preview. iMessage caches
aggressively — if you see a stale card, append `?v=2` to bust it.

### iOS shortcut

Open the site in Safari → Share → **Add to Home Screen**. It picks up
`apple-touch-icon.png` and launches full-screen with no browser chrome, because of
`display: standalone` in the manifest and the `apple-mobile-web-app-*` tags. The stat
strip is padded by `env(safe-area-inset-bottom)` so it clears the home indicator.

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

## Regenerating the artwork

The OG card is drawn from the *actual* ball — same seeds, same Voronoi partition, same
stage colors, and the same flag-over-code billboards the page draws as sprites. It is a
render of the thing, not a mock-up. The camera angle is chosen by searching rotations for
the one showing the most surviving teams.

The icons use `render_football()` instead: a plain truncated icosahedron with one gold
pentagon. At 180px and below the 42 data panels are noise.

```powershell
pip install pillow
python render_assets.py
```

Run it again after the final and the card will show a single gold panel on a dark ball.
Unlike `refresh.py`, this one needs Pillow, and you only need it when the standings change
in a way you want reflected in the share image.

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
