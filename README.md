# spoonscarpets-data

Canonical dataset and seamless Axminster SVG tile archive for every carpeted J D Wetherspoon pub in the UK (**768 vectorized carpets + 8 confirmed carpet-free pubs = 776 total**).

Consumed by [`spoonscarpets.com`](https://spoonscarpets.com) and [`spoons.cheap`](https://spoons.cheap).

## Structure

```text
├── data/
│   └── carpets.json                  # Public catalog (776 pubs, palettes, dimensions, noCarpet notes)
├── patterns/                         # 768 mathematically seamless flat-colour SVGs (<ref>.svg)
├── scripts/
│   ├── verify_seams.py               # Unquantized librsvg/Cairo edge-continuity check
│   ├── render_thumbs.py              # Renders 3×3 WebP grid thumbnails into dist/thumbs/
│   └── build_dist.py                 # Assembles dist/ ready for Cloudflare R2 upload
├── CARPET_VECTORIZATION_PLAYBOOK.md  # Full vectorization & seam-verification spec
└── .github/workflows/
    ├── validate.yml                  # PR validation (schema + 0-seam check)
    └── publish-r2.yml                # Syncs dist/ to Cloudflare R2 (assets.spoonscarpets.com)
```

## Quick Commands

```bash
# Verify catalog integrity + seam continuity on one or all SVGs
python3 scripts/verify_seams.py --catalog-only
python3 scripts/verify_seams.py patterns/6530.svg

# Render 3×3 WebP thumbnails + assemble dist/ for R2
python3 scripts/build_dist.py
```

## Asset URLs (when synced to R2)

- Catalog: `https://assets.spoonscarpets.com/carpets.json`
- Seamless SVG tile: `https://assets.spoonscarpets.com/patterns/<ref>.svg`
- 3×3 WebP thumbnail: `https://assets.spoonscarpets.com/thumbs/<ref>.webp`

## License & Disclaimer

- **Vector patterns (`patterns/`), catalog (`data/carpets.json`), and documentation:** licensed under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** — see [LICENSE](./LICENSE).
- **Scripts & workflows (`scripts/`, `.github/workflows/`):** licensed under the **GNU General Public License v3.0 (GPL-3.0-only)** — see [LICENSE-CODE](./LICENSE-CODE).

This is an independent, unofficial archival project and is not affiliated with or endorsed by J D Wetherspoon plc or any carpet manufacturer. Pub names and underlying physical carpet designs remain the property of their respective owners.
