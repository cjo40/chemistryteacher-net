# chemistryteacher.net

Free interactive chemistry activities. Every file in `activities/` becomes a page:

| File | Web address |
|---|---|
| `activities/gas-laws.html` | chemistryteacher.net/gas-laws |
| `activities/naming-compounds.html` | chemistryteacher.net/naming-compounds |

Cloudflare Pages rebuilds the site about 1 minute after any change is saved here (committed).

## Update an activity (GitHub website only)

1. Name your new version exactly like the old one, e.g. `gas-laws.html`.
2. Open the `activities` folder here → **Add file** → **Upload files** → drop the file in.
3. Click **Commit changes**. The live page updates in about a minute.

The search text, About panel and home-page card come from `site.json`, so they stay when you replace a file.

## Add a new activity

1. Give the file a short, lowercase, hyphenated name that matches how people search, e.g. `limiting-reactant.html`.
2. Upload it to the `activities` folder and commit. It shows up on the home page and sitemap automatically.
3. Optional but better for Google: add an entry for it in `site.json` (copy another activity's entry and change the words), or ask Claude to do it.

## Remove an activity

Open the file in `activities/` → **⋯** menu → **Delete file** → **Commit changes**.

## What's in here

| Item | What it is |
|---|---|
| `activities/` | The activity HTML files, one per page |
| `site.json` | Titles, descriptions, units, About text, old-address redirects |
| `assets/` | Icons, fonts, preview images |
| `build.py` | Builds the site into `public/` (Cloudflare runs `python3 build.py`) |

Cloudflare Pages settings: build command `python3 build.py`, output directory `public`.
